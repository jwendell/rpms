#! /bin/bash
#
# Copyright (c) 2019 Red Hat.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#

set -o pipefail
set -e
set -u
set -x

[ $# -ne 1 ] && echo "Usage: $0 version" && exit 1

# grafana version (must be tagged on github.com/grafana/grafana as "v$VER")
VER=$1
BUILDDIR=`mktemp -d buildXXXXXX`

which npm || (echo Please install \"npm\" package && exit 1)
which wget || (echo Please install \"wget\" package && exit 1)
which git || (echo Please install \"git\" package && exit 1)

# get src tree and set cwd
echo Fetching pristine upstream git tagged branch for grafana version v$VER ...
git clone https://github.com/grafana/grafana grafana-$VER
cd grafana-$VER
git checkout -b v$VER v$VER

# exclude the phantomjs-prebuilt binary module from the webpack
sed -i '/phantomjs-prebuilt/d' package.json

# nuke grunt task for copying phantomjs
rm -f scripts/grunt/options/phantomjs.js
sed -i '/phantomjs/d' scripts/grunt/*.js

# populate node_modules using package.json
echo Running yarn to populate local node_modules ....
npm install yarn
rm -f package-lock.json
node_modules/yarn/bin/yarn --non-interactive --no-progress --ignore-engines install --pure-lockfile > yarn.out 2>&1

# build the webpack
echo;echo Building production webpack ....
node_modules/webpack/bin/webpack.js --display errors-only --mode production --config scripts/webpack/webpack.prod.js

cd ..

# webpack tarball. Includes public/views because index.html references the webpack
tar czf grafana_webpack-$VER.tar.gz grafana-$VER/public/build grafana-$VER/public/views

# source tarball (if needed)
if [ ! -f grafana-$VER.tar.gz ]; then
  wget --quiet -O grafana-$VER.tar.gz https://github.com/grafana/grafana/archive/v$VER/grafana-$VER.tar.gz
fi

# done
echo Both grafana-$VER.tar.gz and grafana_webpack-$VER.tar.gz
echo should now be copied to your \$HOME/rpmbuild/SOURCES

exit 0
