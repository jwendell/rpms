default: test

shell-test:
	find . -name '*.sh' -print0 | xargs -0 -r shellcheck


copr-test:
	./build.sh

test: shell-test copr-test
