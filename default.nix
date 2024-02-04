{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    buildah
    podman
    python3
    qemu
  ];

  shellHook = ''
    alias vim=nvim
  '';
}
