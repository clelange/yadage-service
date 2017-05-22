from setuptools import setup, find_packages

setup(
  name = 'yadage-service',
  version = '0.0.1',
  description = 'yadage workflow web service',
  author = 'Lukas Heinrich',
  author_email = 'lukas.heinrich@cern.ch',
  packages=find_packages(),
  install_requires = [
    'Flask',
    'Flask-AutoIndex',
    'Flask-Login',
    'oauth2',
    'Flask-OAuth',
    'requests[security]',
    'redis',
    'msgpack-python',
    'python-socketio',
    'gevent',
    'gevent-websocket',
    'requests',
  ],
  entry_points = {
  },
  include_package_data = True,
  zip_safe=False,
)
