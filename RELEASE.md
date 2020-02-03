# Release Instructions

1. Change version number in setup.py

1. Add release notes to CHANGELOG.md

1. Build package

  ```bash
  $ rm -rf dist/
  $ python setup.py sdist
  ```

1. Commit changes and tag code

  ```bash
  $ git add . --all
  $ git commit -a -m "bumped version number"
  $ git push origin master
  $ git tag <version-number>
  $ git push --tags
  ```

1. Push changes to PyPI (using twine)

  ```bash
  $ twine upload dist/*
  ```
