# proofpoint_rewrite

This program can be used in conjunction with procmail to remove the proofpoint
url defense urls from an email. A simple rule like below should work.

    :0 fw
    | python3.5 $HOME/bin/remove_proofpoint.py

The program will take stdin, and return the modified content on stdout.

This is a very basic script that assumes a lot. It should rewrite messages
with a single part, or multiplart messages with plain text and html.
