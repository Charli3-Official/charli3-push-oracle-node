{
  description = "charli3-backend-v2";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs?ref=nixos-22.11";
    flake-parts = {
      url = "github:hercules-ci/flake-parts";
      inputs.nixpkgs-lib.follows = "nixpkgs";
    };
    # For plutip-server
    cardano-transaction-lib = {
      url = "github:Plutonomicon/cardano-transaction-lib?ref=develop";
    };
    cardano-node = {
      follows = "cardano-transaction-lib/cardano-node";
    };
    ogmios = {
      follows = "cardano-transaction-lib/ogmios";
    };
  };

  outputs = inputs @ { flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = inputs.nixpkgs.lib.systems.flakeExposed;

      perSystem = { config, self', inputs', pkgs, system, ... }: {
        formatter = pkgs.nixpkgs-fmt;

        devShells.default =
          pkgs.mkShell {
            nativeBuildInputs = [
              pkgs.poetry
              inputs'.cardano-transaction-lib.packages."plutip-server:exe:plutip-server"
              inputs'.ogmios.packages."ogmios:exe:ogmios"
              inputs'.cardano-node.packages.cardano-node
            ];
          };
      };
    };
}
