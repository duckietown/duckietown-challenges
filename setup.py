from setuptools import find_packages, setup


def get_version(filename):
    import ast
    version = None
    with open(filename) as f:
        for line in f:
            if line.startswith('__version__'):
                version = ast.parse(line).body[0].value.s
                break
        else:
            raise ValueError('No version found in %r.' % filename)
    if version is None:
        raise ValueError(filename)
    return version


version = get_version(filename='src/duckietown_challenges/__init__.py')

setup(name='duckietown-challenges',
      version=version,
      download_url='http://github.com/duckietown/duckietown-challenges/tarball/%s' % version,
      package_dir={'': 'src'},
      packages=find_packages('src'),
      install_requires=[
          'termcolor',
          'decorator',
          'PyYAML',
          'python-dateutil',
          'oyaml',
          'numpy',
          'six',
          'future',
          'networkx>=2.2',
          'dataclasses',
      ],

      tests_require=[
      ],

      # This avoids creating the egg file, which is a zip file, which makes our data
      # inaccessible by dir_from_package_name()
      zip_safe=False,

      # without this, the stuff is included but not installed
      include_package_data=True,

      entry_points={
          'console_scripts': [
              'dt-challenges-make-readme-definitions  = duckietown_challenges:make_readmes_main',
              'dt-challenges-make-readme-templates  = duckietown_challenges:make_readmes_templates_main',
          ]
      }
      )
