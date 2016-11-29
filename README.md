# proofpoint_rewrite

This program can be used in conjunction with procmail to remove the proofpoint
url defense urls from an email. A simple rule like below should work.

    :0 fw
    * ^X-Proofpoint.*: .*
    | python3.5 $HOME/bin/remove_proofpoint.py

If you would like to test this out to see how it works with a copy:

    :0c
    * ^X-Proofpoint.*: .*
    {
            :0 fw
            | /usr/bin/python3 $HOME/proofpoint_rewrite-noppcheck.py
            :0
            non-proofpoint
    }

The program will take stdin, and return the modified content on stdout.

This is a very basic script that assumes a lot. It should rewrite messages
with a single part, or multiplart messages with plain text and html.
