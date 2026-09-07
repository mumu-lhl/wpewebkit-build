# wpewebkit-build

Reproducible, relocatable WPEWebKit runtime builds for Ciyue.

The repository contains a manually dispatched GitHub Actions workflow. It
downloads a checksum-pinned upstream WPEWebKit source release, applies the
runtime relocation patch, builds the library and matching helper processes in
a pinned Arch Linux environment, and publishes the result as a GitHub Release.

## Build a release

1. Open **Actions → Build WPEWebKit runtime → Run workflow**.
2. Enter the upstream WPEWebKit version and source archive SHA-256.
3. Increase `release_revision` when rebuilding the same upstream version with
   packaging changes.
4. Run the workflow. A successful build publishes the runtime archive and its
   SHA-256 file under the tag `wpewebkit-VERSION-REVISION`.

Defaults currently build WPEWebKit 2.44.2 for Linux x86_64 with a glibc 2.39
baseline. Inputs are validated before package installation, and source changes
that no longer match the relocation patch fail closed.

## Archive layout

The archive preserves the staged installation layout:

```text
usr/lib/libWPEWebKit-2.0.so*
usr/lib/wpe-webkit-2.0/WPENetworkProcess
usr/lib/wpe-webkit-2.0/WPEWebProcess
usr/lib/wpe-webkit-2.0/injected-bundle/
usr/lib/wpe-webkit-2.0/licenses/THIRD_PARTY_NOTICES
WPEWEBKIT-BUILD-INFO.txt
```

The WPE helper path and injected-bundle path are resolved from the installed
`libWPEWebKit` location. The bubblewrap sandbox remains enabled.

These builds are intended as inputs to Ciyue's Linux packaging process, not as
general-purpose upstream WPEWebKit binary distributions.
