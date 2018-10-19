# coding=utf-8
import argparse
import os
import sys

import yaml
from .challenge import ChallengeDescription

from . import dclogger


def make_readmes_main():
    parser = argparse.ArgumentParser()
    # parser.add_argument('--config', default='challenge.yaml',
    #                     help="YAML configuration file")
    parser.add_argument('-C', dest='cwd', default='.', help='Base directory')

    parsed = parser.parse_args(sys.argv[1:])

    d = parsed.cwd

    f = os.path.join(d, 'challenge.yaml')
    if not os.path.exists(f):
        msg = 'Please run in a directory containing "challenge.yaml".'
        raise Exception(msg)

    basedir, challenge = read_challenge_info(f)

    out = ""

    from .constants import get_duckietown_server_url
    base_url = get_duckietown_server_url()

    # language=markdown
    base = """    
<!-- do not modify - autogenerated -->


# AI Driving Olympics

<a href="http://aido.duckietown.org"><img width="200" src="https://www.duckietown.org/wp-content/uploads/2018/07/AIDO-768x512.png"/></a>


## Challenge "{challenge.title}" - `{challenge.name}`

This is one of the challenges in the [the AI Driving Olympics](http://aido.duckietown.org/).

The [online description of this challenge is here][online].

For submitting, please follow [the instructions available in the book][book].

## Leaderboard 

<img style="width: 24em" src="{DTSERVER}/humans/challenges/{challenge.name}/leaderboard/image.png?"/>

For more details, see [the online leaderboard][leaderboard].


[leaderboard]: {DTSERVER}/humans/challenges/{challenge.name}/leaderboard


[book]: http://docs.duckietown.org/DT18/AIDO/out/

[online]: {DTSERVER}/humans/challenges/{challenge.name}

## Challenge description

{challenge.description}

""".format(challenge=challenge, DTSERVER=base_url).strip()

    out += base

    fn = os.path.join(d, 'README.md')
    with open(fn, 'w') as f:
        f.write(out)

    dclogger.info('written to %s' % fn)

def read_challenge_info(fn):
    contents = open(fn).read()
    data = yaml.load(contents)

    if 'description' not in data or data['description'] is None:
        fnd = os.path.join(os.path.dirname(fn), 'challenge.description.md')
        if os.path.exists(fnd):
            desc = open(fnd).read()
            data['description'] = desc
            msg = 'Read description from %s' % fnd
            dclogger.info(msg)

    base = os.path.dirname(fn)
    challenge = ChallengeDescription.from_yaml(data)
    return base, challenge


if __name__ == '__main__':
    make_readmes_main()
