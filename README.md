[![CircleCI](https://circleci.com/gh/duckietown/duckietown-challenges.svg?style=shield)](https://circleci.com/gh/duckietown/duckietown-challenges)

# Duckietown Challenges Library

The runner is now in [the `duckietown-challenges-runner` repo](https://github.com/duckietown/duckietown-challenges-runner).

## Direct Repo Image Build

This repo image builds standalone:

```bash
docker buildx build --load \
	-t duckietown-challenges-repo:local \
	.
```

The current Dockerfile copies only `setup.py`, `setup.json`, `MANIFEST.in`, and `src/` from this
repo.

The runner, CLI, and server repo images install this package from a sibling checkout using a
`duckietown-challenges` build context.
