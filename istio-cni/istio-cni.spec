%undefine _missing_build_ids_terminate_build

%global git_commit 1e3db221bacf9b9c4e0fbb9fb0665204fa6c4093
%global git_shortcommit  %(c=%{git_commit}; echo ${c:0:7})

%global provider        github
%global provider_tld    com
%global project         maistra
%global repo            istio-cni
%global with_debug 0

# https://github.com/maistra/istio-cni
%global provider_prefix %{provider}.%{provider_tld}/%{project}/%{repo}

Name:           istio-cni
Version:        1.1.0
Release:        1%{?dist}
Summary:        Istio CNI Plugin
License:        ASL 2.0
URL:            https://%{provider_prefix}

Source0:        https://%{provider_prefix}/archive/%{git_commit}/%{repo}-%{git_commit}.tar.gz

# e.g. el6 has ppc64 arch without gcc-go, so EA tag is required
ExclusiveArch:  %{?go_arches:%{go_arches}}%{!?go_arches:%{ix86} x86_64 aarch64 %{arm}}
# If go_compiler is not set to 1, there is no virtual provide. Use golang instead.
BuildRequires:  golang >= 1.13

%description
istio-cni is a Container Network Interface (CNI) Plugin that sets up Istio iptables rules for a Pod.

%prep
rm -rf istio-cni
mkdir -p istio-cni/src/%{provider_prefix}
tar zxf %{SOURCE0} -C istio-cni/src/%{provider_prefix} --strip=1

%build
cd istio-cni
export GOPATH=$(pwd):%{gopath}

pushd src/%{provider_prefix}
make build ISTIO_OUT=bin ISTIO_CNI_RELPATH=github.com/maistra/istio-cni TAG=dummy

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/opt/cni/bin
cd istio-cni/src/%{provider_prefix}

install -p -m 755 tools/deb/istio-iptables.sh %{buildroot}/opt/cni/bin
install -p -m 755 deployments/kubernetes/install/scripts/install-cni.sh %{buildroot}
install -p -m 644 deployments/kubernetes/install/scripts/filter.jq %{buildroot}
install -p -m 755 deployments/kubernetes/install/scripts/istio-cni.conf.default %{buildroot}/istio-cni.conf.tmp

%if 0%{?with_debug}
	install -p -m 755 bin/istio-cni %{buildroot}/opt/cni/bin
%else
	echo "Dumping dynamic symbols"
	nm -D bin/istio-cni --format=posix --defined-only \
	| awk '{ print $1 }' | sort > dynsyms

	echo "Dumping function symbols"
	nm bin/istio-cni --format=posix --defined-only \
	| awk '{ if ($2 == "T" || $2 == "t" || $2 == "D") print $1 }' \
	| sort > funcsyms

	echo "Grabbing other function symbols"
	comm -13 dynsyms funcsyms > keep_symbols

	echo "Removing unnecessary debug info"
	COMPRESSED_NAME=istio_cni_debuginfo

	objcopy -S --remove-section .gdb_index --remove-section .comment \
	--keep-symbols=keep_symbols bin/istio-cni  $COMPRESSED_NAME

	echo "Stripping binary"
	mkdir stripped
	strip -o stripped/istio-cni -s bin/istio-cni

	echo "Compressing debugdata"
	xz $COMPRESSED_NAME

	echo "Injecting compressed data into .gnu_debugdata"
	objcopy --add-section .gnu_debugdata=$COMPRESSED_NAME.xz stripped/istio-cni

	cp -pav stripped/istio-cni %{buildroot}/opt/cni/bin
%endif

%files
%license istio-cni/src/%{provider_prefix}/LICENSE
%doc     istio-cni/src/%{provider_prefix}/README.md

/opt/cni/bin/istio-cni
/opt/cni/bin/istio-iptables.sh
/install-cni.sh
/filter.jq
/istio-cni.conf.tmp


%changelog
* Tue Mar 31 2020 Jonh Wendell <jwendell@redhat.com> - 1.1.0-1
- First 1.1 version
