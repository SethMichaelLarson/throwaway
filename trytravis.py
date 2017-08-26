#             Copyright (C) 2017 Seth Michael Larson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Send your local git repo changes to Travis CI without needless commits and pushes. """

import time
import getpass
import platform
import sys
import os
import re
import colorama
import git


__title__ = 'trytravis'
__author__ = 'Seth Michael Larson'
__email__ = 'sethmichaellarson@protonmail.com'
__description__ = 'Send your local git repo changes to Travis CI without needless commits and pushes.'
__license__ = 'Apache-2.0'
__url__ = 'https://github.com/SethMichaelLarson/trytravis'
__version__ = '0.0.0.dev0'

__all__ = ['main', 'TryTravis']

# Try to find the home directory for different platforms.
_home_dir = os.path.expanduser('~')
if _home_dir == '~' or not os.path.isdir(_home_dir):
    try:  # Windows
        import win32file  # noqa: F401
        from win32com.shell import shell, shellcon
        home = shell.SHGetFolderPath(0, shellcon.CSIDL_PROFILE, None, 0)
    except ImportError:  # Try common directories?
        for _home_dir in [os.environ.get('HOME', ''),
                          '/home/%s' % getpass.getuser(),
                          'C:\\Users\\%s' % getpass.getuser()]:
            if os.path.isdir(_home_dir):
                break

# Determine config directory.
if platform.system() == 'Windows':
    config_dir = os.path.join(_home_dir, 'trytravis')
else:
    config_dir = os.path.join(_home_dir, '.config', 'trytravis')
del _home_dir

try:
    user_input = raw_input
except NameError:
    user_input = input


class TryTravis(object):
    """ Object which can be used to submit jobs via `trytravis` programmatically. """
    def __init__(self, path):
        self.path = path
        self.slug = None
        self.build = None
        self.build_url = None

    def start(self):
        self._load_trytravis_github_slug()
        self._submit_project_to_github()
        self._wait_for_travis_build()
        self._watch_travis_build()

    def _load_trytravis_github_slug(self):
        try:
            with open(os.path.join(config_dir, 'slug'), 'r') as f:
                self.slug = f.read()
        except (OSError, IOError):
            raise RuntimeError('Could not find your repository. Have you ran `trytravis --repo`?')

    def _submit_project_to_github(self):
        repo = git.Repo(self.path)
        old_branch = repo.active_branch.name
        try:
            new_branch = 'trytravis-' + str(int(time.time() * 1000))
            repo.git.checkout('HEAD', b=new_branch)
            repo.git.add('--all')
            repo.git.commit(m='trytravis')
            try:
                remote = repo.create_remote('trytravis', 'https://github.com/' + self.slug)
            except:
                pass
            remote.push()
        finally:
            try:
                repo.delete_remote('trytravis')
            except:
                pass
            repo.git.checkout(old_branch)

    def _wait_for_travis_build(self):
        raise NotImplementedError()

    def _watch_travis_build(self):
        colorama.init()
        raise NotImplementedError()


def main(argv=None):
    """ Main entry point when the user runs the `trytravis` command. """
    try:
        colorama.init()
        if argv is None:
            argv = sys.argv[1:]

        token_input_argv = len(argv) == 2 and argv[0] in ['--token', '-t', '-T']

        # We only support a single argv parameter.
        if len(argv) > 1 and not token_input_argv:
            main(['--help'])

        # Parse the command and do the right thing.
        if len(argv) == 1 or token_input_argv:
            arg = argv[0]

            # Help/usage
            if arg in ['-h', '--help', '-H']:
                print('usage: trytravis [command]?\n'
                      '\n'
                      '  [empty]               Running with no command submits your git repo to Travis.\n'
                      '  --help, -h            Prints this help string.\n'
                      '  --version, -v         Prints out the version, useful when submitting an issue.\n'
                      '  --repo, -r [repo]?    Tells the program you wish to setup your building repository.\n'
                      '\n'
                      'If you\'re still having troubles feel free to open an issue at our\n'
                      'issue tracker: https://github.com/SethMichaelLarson/trytravis/issues')

            # Version
            elif arg in ['-v', '--version', '-V']:
                platform_system = platform.system()
                if platform_system == 'Linux':
                    name, version, _ = platform.dist()
                else:
                    name = platform_system
                    version = platform.version()
                print('trytravis %s (%s %s, python %s)' % (__version__,
                                                           name.lower(),
                                                           version,
                                                           platform.python_version()))

            # Token
            elif arg in ['-r', '--repo', '-R']:
                if len(argv) == 2:
                    url = argv[1]
                else:
                    url = user_input('Input the URL of the GitHub repository to use as a `trytravis` repository: ')
                url = url.strip()
                match = re.match(r'^https://(?:www\.)?github.com/([^/]+)/([^/]+)$', url)
                if not match:
                    raise RuntimeError('That URL doesn\'t look like a valid GitHub URL. We expect something'
                                       'of the form: `https://github.com/[USERNAME]/[REPOSITORY]`')

                # Make sure that the user actually wants to use this repository.
                author, name = match.groups()
                accept = user_input('Remember that `trytravis` will make commits on your behalf to '
                                    '`https://github.com/%s/%s`. Are you sure you wish to use this '
                                    'repository? Type `y` or `yes` to accept: ' % (author, name))
                if accept.lower() not in ['y', 'yes']:
                    raise RuntimeError('Operation aborted by user.')

                if not os.path.isdir(config_dir):
                    os.makedirs(config_dir)
                with open(os.path.join(config_dir, 'slug'), 'w+') as f:
                    f.truncate()
                    f.write('/%s/%s' % (author, name))
                print('Repository saved successfully.')

        # No arguments means we're trying to submit to Travis.
        elif len(argv) == 0:
            trytravis = TryTravis(os.getcwd())
            trytravis.start()
    except RuntimeError as e:
        print(colorama.Fore.RED + 'ERROR: ' + str(e) + colorama.Style.RESET_ALL)
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
