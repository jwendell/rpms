# Generate devel rpm
%global with_devel 0
# Build with debug info rpm
%global with_debug 0
# Run unit tests
%global with_tests 0
# Build test binaries
%global with_test_binaries 0

%if 0%{?with_debug}
%global _dwz_low_mem_die_limit 0
%else
%global debug_package   %{nil}
%endif

%global git_commit 35061cebc6f2327b0e4b4bef9e558c5892216a67
%global git_shortcommit  %(c=%{git_commit}; echo ${c:0:7})

%global provider        github
%global provider_tld    com
%global project         maistra
%global repo            istio-operator

# are we building community or product rpms
%global community_build  true

# https://github.com/maistra/istio-operator
%global provider_prefix %{provider}.%{provider_tld}/%{project}

# Use /usr/local as base dir, once upstream heavily depends on that
%global _prefix /usr/local

Name:           istio-operator
Version:        1.1.0
Release:        1%{?dist}
Summary:        A Kubernetes operator to manage Istio.
License:        ASL 2.0
URL:            https://%{provider_prefix}/%{repo}

Source0:        https://%{provider_prefix}/%{repo}/archive/%{git_commit}/%{repo}-%{git_commit}.tar.gz

# e.g. el6 has ppc64 arch without gcc-go, so EA tag is required
ExclusiveArch:  %{?go_arches:%{go_arches}}%{!?go_arches:%{ix86} x86_64 aarch64 %{arm}}
# If go_compiler is not set to 1, there is no virtual provide. Use golang instead.
BuildRequires:  golang >= 1.13

%description
Istio-operator is a kubernetes operator to manage the lifecycle of Istio.

%if 0%{?with_devel}
%package devel
Summary:       %{summary}
BuildArch:     noarch

%description devel
Istio-operator is a kubernetes operator to manage the lifecycle of Istio.
%endif

%prep

rm -rf OPERATOR

mkdir -p OPERATOR/src/github.com/maistra/istio-operator
tar zxf %{SOURCE0} -C OPERATOR/src/github.com/maistra/istio-operator --strip=1

%build
cd OPERATOR
export GOPATH=$(pwd):%{gopath}
pushd src/github.com/maistra/istio-operator/
COMMUNITY=%{community_build} GO111MODULE=on VERSION=%{version}-%{release} GITREVISION=%{git_shortcommit} GITSTATUS=Clean GITTAG=%{version} make compile collect-resources
popd

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT%{_bindir}
pushd OPERATOR/src/github.com/maistra/istio-operator/tmp/_output/bin/

%if 0%{?with_debug}
    cp -pav istio-operator $RPM_BUILD_ROOT%{_bindir}/
%else
    mkdir stripped

    echo "Dumping dynamic symbols"
        nm -D istio-operator --format=posix --defined-only \
  | awk '{ print $1 }' | sort > dynsyms

       echo "Dumping function symbols"
       nm istio-operator --format=posix --defined-only \
  | awk '{ if ($2 == "T" || $2 == "t" || $2 == "D") print $1 }' \
  | sort > funcsyms

        echo "Grabbing other function symbols"
        comm -13 dynsyms funcsyms > keep_symbols


  COMPRESSED_NAME="operator_debuginfo"
        echo "remove unnecessary debug info"
        objcopy -S --remove-section .gdb_index --remove-section .comment \
  --keep-symbols=keep_symbols "istio-operator" "${COMPRESSED_NAME}"

        echo "stripping operator"
        strip -o "stripped/istio-operator" -s istio-operator


        echo "compress debugdata for istio-operator into ${COMPRESSED_NAME}.xz"
        xz "${COMPRESSED_NAME}"

        echo "inject compressed data into .gnu_debugdata for istio-operator"
        objcopy --add-section ".gnu_debugdata=${COMPRESSED_NAME}.xz" "stripped/istio-operator"

        cp -pav "stripped/istio-operator" "${RPM_BUILD_ROOT}%{_bindir}/"
%endif
popd

mkdir -p $RPM_BUILD_ROOT%{_datadir}/istio-operator/helm
TEMPLATES_DIR=$RPM_BUILD_ROOT/%{_datadir}/istio-operator/default-templates
mkdir -p ${TEMPLATES_DIR}

pushd OPERATOR/src/github.com/maistra/istio-operator/tmp/_output/resources
# install the charts
cp -rpavT helm/ $RPM_BUILD_ROOT%{_datadir}/istio-operator/helm
# install the templates
cp -rpavT default-templates/ $RPM_BUILD_ROOT%{_datadir}/istio-operator/default-templates

#install manifests
cp -rpavT manifests/ $RPM_BUILD_ROOT/manifests
popd

%files
%{_bindir}/istio-operator
%{_datadir}/istio-operator
/manifests

%changelog
* Tue Feb 25 2020 Brian Avery <bavery@redhat.com> - 1.1.0-1
- Update to Maistra 1.1
