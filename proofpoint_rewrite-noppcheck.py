#!/usr/bin/python
# coding: utf8
'''
This program can be used in conjunction with procmail to remove the proofpoint
url defense urls from an email. A simple rule like below should work.

:0 fw
* ^X-Proofpoint.*: .*
| python3 $HOME/bin/remove_proofpoint.py

The program will take stdin, and return the modified content on stdout.
This is a very basic script that assumes a lot. It should rewrite messages
with a single part, or multiplart messages with plain text and html.
Joe Shamblin <wjs at cs.duke.edu>
'''

from urllib.parse import urlparse, parse_qs
import base64
import email
import re
import quopri
import sys
from io import StringIO
from email.generator import Generator

# deal with unicode issues
import codecs
sys.stdout = codecs.getwriter("iso-8859-1")(sys.stdout.detach())

pp_url = re.compile(r'(https://urldefense.proofpoint.com/v2/url\?u=.*?(&|&amp;)e=)')
message = email.message_from_string(sys.stdin.read())


def revert_ppurls(c):
    """
    Take in text and replace all proofpoint url defense urls.

    with the original url
    """
    for match in pp_url.finditer(c):
        url = parse_qs(urlparse(match.group(0)).query)
        tmp = url['u'][0].replace('_', '/')
        # replace the hexidecimal encoding with the unicode entry
        # ref: https://github.com/warquel/ppdecode
        for m in set(re.findall('-[0-9A-F]{2}', tmp)):
            tmp = tmp.replace(m, chr(int(m[1:3], 16)))
        c = c.replace(match.group(0), tmp.rstrip())
    return c

# this should deal with either single messages or flat multipart messages.
# A more thorough approach would be needed for complex mime trees
# ref. http://blog.magiksys.net/parsing-email-using-python-content


if message.is_multipart():
    for part in message.walk():
        content_transfer = part.__getitem__('Content-Transfer-Encoding')
        charset = part.get_content_charset()
        content_type = part.get_content_type()
        if content_type in ['text/html', 'text/plain']:
            _content = part.get_payload(decode=True).decode('iso-8859-1')
            _payload = revert_ppurls(_content)
            if content_transfer and content_transfer.lower() == 'base64':
                part.set_payload(base64.encodestring(_payload.encode('iso-8859-1')))
            elif content_transfer and  content_transfer.lower() == 'quoted-printable':
                part.set_payload(quopri.encodestring(_payload.encode('iso-8859-1')))
            else:
                part.set_payload(_payload)
else:
    content_transfer = message.__getitem__('Content-Transfer-Encoding')
    charset = message.get_content_charset()
    _payload = revert_ppurls(message.get_payload(decode=True).decode('iso-8859-1'))
    if content_transfer and  content_transfer.lower() == 'base64':
        message.set_payload(base64.encodestring(_payload.encode('iso-8859-1')))
    elif content_transfer and content_transfer.lower() == 'quoted-printable':
        message.set_payload(quopri.encodestring(_payload.encode('iso-8859-1')))
    else:
        message.set_payload(_payload)

fp = StringIO()
g = Generator(fp, mangle_from_=True, maxheaderlen=60)
g.flatten(message, unixfrom=True)
text = fp.getvalue()
sys.stdout.write(text)
