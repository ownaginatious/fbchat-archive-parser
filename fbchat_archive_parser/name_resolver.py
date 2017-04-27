from __future__ import unicode_literals

import json
import re

from bs4 import BeautifulSoup
import requests
from requests.exceptions import RequestException
import six

_EMAIL_REMOVER = re.compile(r"@facebook.com$")
_MANUAL_NAME_MATCHER = re.compile(r"<span id=\"fb-timeline-cover-name\">([^<]+)</span>")


class FacebookRequestError(Exception):
    pass


class FacebookNameResolver(object):

    def __init__(self, username, password):
        self._cached_profiles = None
        self.username = username
        self.password = password
        self._session = None

    def _login(self):
        if self._session:
            return
        payload = {
            'email': self.username,
            'pass': self.password
        }
        self._session = requests.Session()
        page = self._session.get(
            'https://www.facebook.com/', allow_redirects=False
        )
        page_parsed = BeautifulSoup(page.text, 'html.parser')
        for e in page_parsed.select("#login_form input[type='hidden']"):
            payload[e['name']] = e['value']
        cookies = None
        # Apparently all you need is the `_js_datr` cookie from the page
        # to trick Facebook into thinking your cookies are working.
        for script in page_parsed.findAll('script'):
            datr_search = re.search(
                r'\["_js_datr","([^"]*)"', script.text, re.DOTALL
            )
            if datr_search:
                datr = datr_search.group(1)
                cookies = {'_js_datr': datr}
                break
        if not cookies:
            raise Exception
        page = self._session.post(
            'https://www.facebook.com/login.php?login_attempt=1&lwv=110',
            allow_redirects=True, timeout=10, data=payload, cookies=cookies
        )
        try:
            page.raise_for_status()
        except RequestException as req_error:
            raise FacebookRequestError(str(req_error))

        # If the login button ID is still around, we probably failed to log in.
        if 'id="loginbutton"' in page.text:
            raise FacebookRequestError("Bad Facebook credentials")

        # Extract the profile ID. Unfortunately, there aren't many reliable
        # ways for grabbing this data, as a lot of the nicely structured
        # sources are generated in JavaScript.
        matcher = re.search(
            r'\["CurrentUserInitialData",\[\],'
            r'{"USER_ID":"(?P<profile_id>[0-9]+)"',
            page.text
        )
        if matcher:
            return int(matcher.group('profile_id'))
        else:
            raise FacebookRequestError(
                'Error extracting logged-in user profile UID'
            )

    def _parse_id(self, facebook_id):
        try:
            if isinstance(facebook_id, six.string_types):
                return int(_EMAIL_REMOVER.sub(r'', facebook_id))
        except ValueError:
            pass

    def _cache(self):
        if self._cached_profiles is not None:
            return self._cached_profiles
        profile_id = self._login()

        resp = self._session.get(
            'https://www.facebook.com/ajax/typeahead/search'
            '/facebar/bootstrap/',
            allow_redirects=True, timeout=10,
            params={
                'filter[0]': 'user',
                'context': 'facebar',
                'viewer': profile_id,
                'token': 'v7',
                'lazy': '0',
                '__user': profile_id,
                '__a': 1
            }
        )
        self._cached_profiles = {}
        data = json.loads(resp.text.replace('for (;;);', ''))
        try:
            for entry in data['payload']['entries']:
                if 'names' not in entry:
                    continue
                self._cached_profiles[entry['uid']] = entry['names'][0]
                if len(entry['names']) > 1:
                    for name in entry['names'][1:]:
                        self._cached_profiles[name] = entry['names'][0]
        except Exception as e:
            raise FacebookRequestError(
                'Strangely formed user entry in Facebook response: %s' % str(e)
            )

        return self._cached_profiles

    def _manual_lookup(self, facebook_id, facebook_id_string):
        """
        People who we have not communicated with in a long time
        will not appear in the look-ahead cache that Facebook keeps.
        We must manually resolve them.

        :param facebook_id: Profile ID of the user to lookup.
        :return:
        """
        resp = self._session.get(
            'https://www.facebook.com/%s' % facebook_id,
            allow_redirects=True, timeout=10
        )
        # No point in trying to get this using BeautifulSoup. The HTML here
        # is the very epitome of what it is to be invalid...
        m = _MANUAL_NAME_MATCHER.search(resp.text)
        if m:
            name = m.group(1)
        else:
            name = facebook_id_string
        self._cached_profiles[facebook_id] = name
        return name

    def resolve(self, facebook_id_string):
        facebook_id = self._parse_id(facebook_id_string)
        if not facebook_id:
            return facebook_id_string
        resolved = self._cache().get(facebook_id)
        if resolved:
            return resolved
        return self._manual_lookup(facebook_id, facebook_id_string)


class DummyNameResolver(FacebookNameResolver):

    def __init__(self):
        super(DummyNameResolver, self).__init__(None, None)
        self._cached_profiles = {}

    def resolve(self, facebook_id_string):
        return facebook_id_string
