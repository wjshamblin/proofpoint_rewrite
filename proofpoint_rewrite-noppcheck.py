#!/usr/bin/python
#coding: iso-8859-1

'''
This program can be used in conjunction with procmail to remove the proofpoint
url defense urls from an email. A simple rule like below should work.

:0 fw
* ^X-Proofpoint.*: .*
| python3 $HOME/bin/remove_proofpoint.py

The program will take stdin, and return the modified content on stdout.
This is a very basic script that assumes a lot. It should rewrite messages
with a single part, or multipart messages with plain text and html.
Joe Shamblin <wjs at cs.duke.edu>
'''

from urllib.parse import urlparse, parse_qs, unquote
from html import unescape
import base64
import email
import re
import quopri
import string
import sys
from io import StringIO
from email.generator import Generator

# deal with unicode issues
import codecs
sys.stdout = codecs.getwriter("iso-8859-1")(sys.stdout.detach())

def decode_proofpoint(pp_encoded_url):
    '''
    Select which version to decode.
    '''
    pp_version_pattern = re.compile(r'https://urldefense\.(?:proofpoint\.)?com/v(?P<version>\d).*?')
    pp_version = pp_version_pattern.search(pp_encoded_url)
    if pp_version:
        if pp_version.group('version') == '2':
            return decode_v2(pp_encoded_url)
        if pp_version.group('version') == '3':
            return decode_v3(pp_encoded_url)
    else:
        raise ValueError('Unknown ProofPoint Version')

def decode_v2(pp_encoded_url):
    '''
    Decode version 2 Proofpoint URLs
    '''
    # V2 variables
    pp_url_pattern = re.compile(r'(https://urldefense.proofpoint.com/v2/url\?u=.*?&e=$)')
    match = pp_url_pattern.search(pp_encoded_url)
    url = parse_qs(urlparse(match.group(0)).query)
    tmp = url['u'][0].replace('_', '/')
    # replace the hexidecimal encoding with the unicode entry
    # ref: https://github.com/warquel/ppdecode
    for m in set(re.findall('-[0-9A-F]{2}', tmp)):
        tmp = tmp.replace(m, chr(int(m[1:3], 16)))
    return unquote(tmp.rstrip())

def decode_v3(pp_encoded_url):
    '''
    Decode version 3 Proofpoint URLs. Proofpoint v3 URLs have the following structure
    https://urldefense.com/v3/__ENCODED_URL__;ENCODED_BYTES!!OToaGQ!89P7bD95-sDCzIxLkYEbM1R_hlGjs6GVKoFbm915ANS356MjJHkgLbB4Vwjpyq0$
    The Encoded URL looks like:

    https://nl.nytimes.com/f/a/P9ApJ1EErQ6SE9JsTzyvbw**A/AAAAAQA*/RgRgPOXCP0TwaHR0cHM6Ly93d3cubnl0aW1lcy5jb20vaW50ZXJhY3RpdmUvMjAyMC8wMi8yOC9zcG9ydHMvd29tZW5zLW9seW1waWMtbWFyYXRob24tdHJpYWxzLmh0bWw_dGU9MSZubD1ydW5uaW5nJmVtYz1lZGl0X3J1XzIwMjAwMjI5JmNhbXBhaWduX2lkPTM1Jmluc3RhbmNlX2lkPTE2MzY3JnNlZ21lbnRfaWQ9MjE3NTAmdXNlcl9pZD0zZmRiZDc0NjU3ZDAxMTFjYjkxMGZkOTczZDcyNWZjYiZyZWdpX2lkPTMxOTE0MzIwMjAwMjI5VwNueXRCCgAqwmBaXskvuFRSD3dqc0Bjcy5kdWtlLmVkdVgEAAAAAA**A

    The *s are separators. A single * gets replaced with its corresponding decoded byte. While ** followed by a
    letter, -, or _ determines how many escaped characters to replace. In the above URL, there are three groups of
    escaped URLs.

    base_url: https://nl.nytimes.com/f/a/P9ApJ1EErQ6SE9JsTzyvbw
    **A /AAAAAQA
    * /RgRgPOXCP0TwaHR0cHM6Ly93d3cubnl0aW1lcy5jb20vaW50ZXJhY3RpdmUvMjAyMC8wMi8yOC9zcG9ydHMvd29tZW5zLW9seW1waWMtbWFyYXRob24tdHJpYWxzLmh0bWw_dGU9MSZubD1ydW5uaW5nJmVtYz1lZGl0X3J1XzIwMjAwMjI5JmNhbXBhaWduX2lkPTM1Jmluc3RhbmNlX2lkPTE2MzY3JnNlZ21lbnRfaWQ9MjE3NTAmdXNlcl9pZD0zZmRiZDc0NjU3ZDAxMTFjYjkxMGZkOTczZDcyNWZjYiZyZWdpX2lkPTMxOTE0MzIwMjAwMjI5VwNueXRCCgAqwmBaXskvuFRSD3dqc0Bjcy5kdWtlLmVkdVgEAAAAAA
    **A

    for a concrete example, take this URL, first unquote (https://docs.python.org/3/library/urllib.parse.html#url-quoting)

    https://urldefense.com/v3/__https://nl.nytimes.com/f/a/P9ApJ1EErQ6SE9JsTzyvbw**A/AAAAAQA*/RgRgPOXCP0TwaHR0cHM6Ly93d3cubnl0aW1lcy5jb20vaW50ZXJhY3RpdmUvMjAyMC8wMi8yOC9zcG9ydHMvd29tZW5zLW9seW1waWMtbWFyYXRob24tdHJpYWxzLmh0bWw_dGU9MSZubD1ydW5uaW5nJmVtYz1lZGl0X3J1XzIwMjAwMjI5JmNhbXBhaWduX2lkPTM1Jmluc3RhbmNlX2lkPTE2MzY3JnNlZ21lbnRfaWQ9MjE3NTAmdXNlcl9pZD0zZmRiZDc0NjU3ZDAxMTFjYjkxMGZkOTczZDcyNWZjYiZyZWdpX2lkPTMxOTE0MzIwMjAwMjI5VwNueXRCCgAqwmBaXskvuFRSD3dqc0Bjcy5kdWtlLmVkdVgEAAAAAA**A__;fn5-fn4!!OToaGQ!89P7bD95-sDCzIxLkYEbM1R_hlGjs6GVKoFbm915ANS356MjJHkgLbB4Vwjpyq0$']

    the encoded bytes are:  fn5-fn4
    which decodes to: ~~~~~

    the A in run_values has a value of 2 so append "~~" to the base_url, incrementing the counter for matches.

    https://nl.nytimes.com/f/a/P9ApJ1EErQ6SE9JsTzyvbw~~/AAAAAQA

    the * translates to a single ~

    https://nl.nytimes.com/f/a/P9ApJ1EErQ6SE9JsTzyvbw~~/AAAAAQA~/RgRgPOXCP0TwaHR0cHM6Ly93d3cubnl0aW1lcy5jb20vaW50ZXJhY3RpdmUvMjAyMC8wMi8yOC9zcG9ydHMvd29tZW5zLW9seW1waWMtbWFyYXRob24tdHJpYWxzLmh0bWw_dGU9MSZubD1ydW5uaW5nJmVtYz1lZGl0X3J1XzIwMjAwMjI5JmNhbXBhaWduX2lkPTM1Jmluc3RhbmNlX2lkPTE2MzY3JnNlZ21lbnRfaWQ9MjE3NTAmdXNlcl9pZD0zZmRiZDc0NjU3ZDAxMTFjYjkxMGZkOTczZDcyNWZjYiZyZWdpX2lkPTMxOTE0MzIwMjAwMjI5VwNueXRCCgAqwmBaXskvuFRSD3dqc0Bjcy5kdWtlLmVkdVgEAAAAAA

    the **A translates again to 2, which is the number of remaining decoded bytes so append ~~ to the end of the URL to get:

    https://nl.nytimes.com/f/a/P9ApJ1EErQ6SE9JsTzyvbw~~/AAAAAQA~/RgRgPOXCP0TwaHR0cHM6Ly93d3cubnl0aW1lcy5jb20vaW50ZXJhY3RpdmUvMjAyMC8wMi8yOC9zcG9ydHMvd29tZW5zLW9seW1waWMtbWFyYXRob24tdHJpYWxzLmh0bWw_dGU9MSZubD1ydW5uaW5nJmVtYz1lZGl0X3J1XzIwMjAwMjI5JmNhbXBhaWduX2lkPTM1Jmluc3RhbmNlX2lkPTE2MzY3JnNlZ21lbnRfaWQ9MjE3NTAmdXNlcl9pZD0zZmRiZDc0NjU3ZDAxMTFjYjkxMGZkOTczZDcyNWZjYiZyZWdpX2lkPTMxOTE0MzIwMjAwMjI5VwNueXRCCgAqwmBaXskvuFRSD3dqc0Bjcy5kdWtlLmVkdVgEAAAAAA~~

    '''
    pp_pattern = re.compile(r'v3/__(?P<url>.+?)__;(?P<enc_bytes>.*?)!')
    token_pattern = re.compile(r'\*(?P<sep>\*.)?(?P<qs>.*?)(?=\*|\Z)')
    # version 3 uses an encoding pattern to decide how many characters to print.
    run_values = string.ascii_uppercase + string.ascii_lowercase + string.digits + '-' + '_'
    # generate a character to length mapping {'A': 2, 'B': 3 ..... '_': 65}
    run_mapping = {j: i + 2 for i, j in enumerate(run_values)}
    match = pp_pattern.search(pp_encoded_url)
    if match:
        match_counter = 0
        end_string = ''
        url = match.group('url')
        encoded_url = unquote(url)
        enc_bytes = match.group('enc_bytes') + '=='
        dec_bytes = (base64.urlsafe_b64decode(enc_bytes)).decode('iso-8859-1')
        tokens = token_pattern.finditer(encoded_url)
        final_url = encoded_url
        if tokens:
            pattern_start = token_pattern.search(encoded_url)
            base_url = encoded_url[0:pattern_start.start()] if pattern_start else ''
            for token in tokens:
                if not token.group('sep'):
                    end_string += dec_bytes[match_counter] + token.group('qs')
                    match_counter += 1
                if token.group('sep'):
                    run_length = run_mapping[token.group('sep')[-1]]
                    end_string += dec_bytes[match_counter:run_length + match_counter] + token.group('qs')
                    match_counter += 1
            if base_url:
                final_url = base_url + end_string
        return final_url
    else:
        raise ValueError('Error parsing URL')

def revert_ppurls(c):
    """
    Take in text and replace all proofpoint url defense urls.
    with the original url
    """
    pp_url_pattern = re.compile(r'(https://urldefense\.(?:proofpoint\.)?com/v\d.*?(&e=$|\$))')
    for match in pp_url_pattern.finditer(c):
        unescaped_url = match.group(0)
        url = unescape(unescaped_url)
        decoded_url = decode_proofpoint(url)
        c = c.replace(unescaped_url, decoded_url)
    return c

# Get the message from stdin
message = email.message_from_string(sys.stdin.read())

# # this should deal with either single messages or flat multipart messages.
# # A more thorough approach would be needed for complex mime trees
# # ref. http://blog.magiksys.net/parsing-email-using-python-content
#
if message.is_multipart():
    for part in message.walk():
        content_transfer = part.__getitem__('Content-Transfer-Encoding')
        charset = part.get_content_charset()
        content_type = part.get_content_type()
        if content_type in ['text/html', 'text/plain']:
            _content = part.get_payload(decode=True).decode('iso-8859-1')
            _payload = revert_ppurls(_content)
            if content_transfer and content_transfer.lower() == 'base64':
                part.set_payload(base64.encodebytes(_payload.encode('iso-8859-1')))
            elif content_transfer and content_transfer.lower() == 'quoted-printable':
                part.set_payload(quopri.encodestring(_payload.encode('iso-8859-1')))
            else:
                part.set_payload(_payload)
else:
    content_transfer = message.__getitem__('Content-Transfer-Encoding')
    charset = message.get_content_charset()
    _payload = revert_ppurls(message.get_payload(decode=True).decode('iso-8859-1'))
    if content_transfer and content_transfer.lower() == 'base64':
        message.set_payload(base64.encodebytes(_payload.encode('iso-8859-1')))
    elif content_transfer and content_transfer.lower() == 'quoted-printable':
        message.set_payload(quopri.encodestring(_payload.encode('iso-8859-1')))
    else:
        message.set_payload(_payload)

fp = StringIO()
g = Generator(fp, mangle_from_=True, maxheaderlen=60)
g.flatten(message, unixfrom=True)
text = fp.getvalue()
sys.stdout.write(text)
