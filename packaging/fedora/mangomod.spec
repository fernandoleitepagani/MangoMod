%global pypi_name mangomod
%global app_id    io.github.mangomod

Name:           mangomod
Version:        0.6.0
Release:        1%{?dist}
Summary:        A polished GTK4/libadwaita GUI configurator for the MangoWM Wayland compositor

License:        MIT
URL:            https://github.com/YOUR-USERNAME/MangoMod
Source0:        %{url}/archive/v%{version}/MangoMod-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3-hatchling
BuildRequires:  python3-build
BuildRequires:  python3-installer
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib

Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Recommends:     wlr-randr

%description
MangoMod is a GTK4/libadwaita application for editing MangoWM
compositor configuration files. It reads and writes MangoWM's flat
`key=value` config format, including all `source=` included files,
and applies changes via `mango msg reload`.

%prep
%autosetup -n MangoMod-%{version}

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files %{pypi_name}

install -Dpm0644 data/%{app_id}.desktop \
  %{buildroot}%{_datadir}/applications/%{app_id}.desktop
install -Dpm0644 data/%{app_id}.metainfo.xml \
  %{buildroot}%{_datadir}/metainfo/%{app_id}.metainfo.xml
install -Dpm0644 data/%{pypi_name}.svg \
  %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/%{app_id}.svg

%check
%pyproject_check_import
desktop-file-validate %{buildroot}%{_datadir}/applications/%{app_id}.desktop
appstream-util validate-relax --nonet \
  %{buildroot}%{_datadir}/metainfo/%{app_id}.metainfo.xml

%files -f %{pyproject_files}
%license LICENSE
%doc README.md CONTRIBUTING.md
%{_bindir}/%{pypi_name}
%{_datadir}/applications/%{app_id}.desktop
%{_datadir}/metainfo/%{app_id}.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/%{app_id}.svg

%changelog
* Sat Sep 20 2026 Your Name <you@example.com> - 0.6.0-1
- Initial package
