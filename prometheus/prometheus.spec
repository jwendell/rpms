# Build with debug info rpm
%global with_debug 0

%if 0%{?with_debug} > 0
%global _dwz_low_mem_die_limit 0
%else
%global debug_package %{nil}
%endif

%global git_commit 7b962f116b97a920a3ea39b287c6ea4748ea418e
%global git_shortcommit  %(c=%{git_commit}; echo ${c:0:7})

Name:           prometheus
Version:        2.14.0
Release:        1%{?dist}
Summary:        An open-source systems monitoring and alerting toolkit
License:        ASL 2.0
URL:            https://prometheus.io/

BuildRequires:  prometheus-promu = 0.5.0
BuildRequires:  golang >= 1.13

Source0:        https://github.com/maistra/prometheus/archive/%{git_commit}.tar.gz

# e.g. el6 has ppc64 arch without gcc-go, so EA tag is required
ExclusiveArch:  %{?go_arches:%{go_arches}}%{!?go_arches:%{ix86} x86_64 aarch64 %{arm}}

%global binary_name prometheus

%description
Prometheus is an open-source systems monitoring and alerting toolkit.

%package prometheus
Summary:  A monitoring and alerting toolkit

%description prometheus
Package containing prometheus files.

%prep

rm -rf PROMETHEUS
mkdir -p PROMETHEUS/src/github.com/prometheus/prometheus
tar zxf %{SOURCE0} -C PROMETHEUS/src/github.com/prometheus/prometheus --strip=1

%build
cd PROMETHEUS
export GOPATH=$(pwd):%{gopath}
cd src/github.com/prometheus/prometheus

PROMU=$(which promu) make -e common-build

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT%{_bindir}
mkdir -p $RPM_BUILD_ROOT%{_datadir}/%{binary_name}/console_libraries/
mkdir -p $RPM_BUILD_ROOT%{_datadir}/%{binary_name}/consoles/
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/%{binary_name}/

binaries=(prometheus promtool tsdbtool)
cd PROMETHEUS/src/github.com/prometheus/prometheus
%if 0%{?with_debug} > 0
  for i in "${binaries[@]}"; do
        cp -pav $i $RPM_BUILD_ROOT%{_bindir}/
   done
%else
    mkdir stripped
    touch keep_symbols
    for i in "${binaries[@]}"; do
       echo "Dumping dynamic symbols for ${i}"
        nm -D $i --format=posix --defined-only \
  | awk '{ print $1 }' | sort > dynsyms

        echo "Dumping function symbols for ${i}"
       nm $i --format=posix --defined-only \
  | awk '{ if ($2 == "T" || $2 == "t" || $2 == "D") print $1 }' \
  | sort > funcsyms

        echo "Grabbing other function symbols from ${i}"
        comm -13 dynsyms funcsyms > keep_symbols

        COMPRESSED_NAME="${i}_debuginfo"
        if [ -s keep_symbols ]; then
          echo "remove unnecessary debug info from ${i}"
          objcopy -S --remove-section .gdb_index --remove-section .comment \
  --keep-symbols=keep_symbols "${i}" "${COMPRESSED_NAME}"
        fi

        echo "stripping: ${i}"
        strip -o "stripped/${i}" -s $i

        if [ -f ${COMPRESSED_NAME} ]; then
          echo "compress debugdata for ${i} into ${COMPRESSED_NAME}.xz"
          xz "${COMPRESSED_NAME}"

          echo "inject compressed data into .gnu_debugdata for ${i}"
          objcopy --add-section ".gnu_debugdata=${COMPRESSED_NAME}.xz" "stripped/${i}"
        fi

        cp -pav "stripped/${i}" "${RPM_BUILD_ROOT}%{_bindir}/"
    done
%endif

cp -a console_libraries/ $RPM_BUILD_ROOT%{_datadir}/%{binary_name}
ln -sf %{_datadir}/%{binary_name}/console_libraries/ $RPM_BUILD_ROOT%{_sysconfdir}/%{binary_name}/
cp -a consoles/ $RPM_BUILD_ROOT%{_datadir}/%{binary_name}/
ln -sf %{_datadir}/%{binary_name}/consoles/ $RPM_BUILD_ROOT%{_sysconfdir}/%{binary_name}/
cp -a documentation/examples/prometheus.yml $RPM_BUILD_ROOT%{_sysconfdir}/%{binary_name}/%{binary_name}.yml

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

%files
%license PROMETHEUS/src/github.com/prometheus/prometheus/LICENSE
%doc     PROMETHEUS/src/github.com/prometheus/prometheus/README.md
%{_bindir}/prometheus
%{_bindir}/promtool
%{_bindir}/tsdbtool
%{_datadir}/%{binary_name}/console_libraries/
%{_sysconfdir}/%{binary_name}/console_libraries
%{_datadir}/%{binary_name}/consoles/
%{_sysconfdir}/%{binary_name}/consoles
%config(noreplace) %{_sysconfdir}/%{binary_name}/%{binary_name}.yml

%changelog
* Tue Jan 28 2020 Daniel Grimm <dgrimm@redhat.com> - 2.14.0-1
- Update to Prometheus v2.14.0
