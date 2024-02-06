{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    buildah
    kind
    kubectl
    kubernetes-helm
    podman
    python3
    qemu
  ];

  shellHook = ''
    alias vim=nvim
    source venv/bin/activate
    export PS1="(venv) \[\033[1;32m\][nix-shell:\w]\$\[\033[0m\] "
  '';
}
