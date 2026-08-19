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
          pkgs.python3
        ];
        shellHook = ''
          export LD_LIBRARY_PATH="${
            pkgs.lib.makeLibraryPath [
              pkgs.stdenv.cc.cc.lib
              pkgs.zlib
              pkgs.libGL
              pkgs.glib
              pkgs.xorg.libX11
              pkgs.xorg.libXext
              pkgs.xorg.libXrender
              pkgs.xorg.libXinerama
              pkgs.xorg.libXi
              pkgs.xorg.libXrandr
              pkgs.xorg.libXcursor
              pkgs.xorg.libXfixes
              pkgs.libxcb
            ]
          }:$LD_LIBRARY_PATH"
        '';
      };
    };
}
