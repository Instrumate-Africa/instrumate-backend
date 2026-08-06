{
  description = "Instrumate devshell";
  inputs = {
    nixpkgs.url = "nixpkgs/nixos-25.11";
  };
  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        nativeBuildInputs = [
          pkgs.pyright
        ];
        buildInputs = [
          pkgs.python3
        ];
        shellHook = ''
          export LD_LIBRARY_PATH="${
            pkgs.lib.makeLibraryPath [
              pkgs.stdenv.cc.cc.lib
            ]
          }:$LD_LIBRARY_PATH"
        '';
      };
    };
}
