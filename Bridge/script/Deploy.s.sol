// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "forge-std/Script.sol";
import "forge-std/console.sol";
import "../src/Source.sol";
import "../src/Destination.sol";

contract DeployScript is Script {
// List of ERC20 token addresses from erc20s.csv

    address[] tokensToBridge = [
        0xc677c31AD31F73A5290f5ef067F8CEF8d301e45c,
        0x0773b81e0524447784CcE1F3808fed6AaA156eC8
    ];
  function run() external {
      // Load deployer private key
      uint256 key = vm.envUint("PRIVATE_KEY");
      address deployer = vm.addr(key);
      console.log("Using deployer:", deployer);
      console.log("Current chain ID:", block.chainid);

      vm.startBroadcast(key);
      if (block.chainid == 43113) {
          _deploySource(deployer);
      } else if (block.chainid == 97) {
          _deployDestination(deployer);
      } else {
          console.log("Chain not supported, id:", block.chainid);
      }
      vm.stopBroadcast();
  }

  function _deploySource(address admin) internal {
      console.log("\n=== Deploying Source on Avalanche Fuji ===");
      Source src = new Source(admin);
      console.log("Source address:", address(src));

      console.log("\n=== Registering Bridgeable Tokens ===");
      for (uint i = 0; i < tokensToBridge.length; i++) {
          address t = tokensToBridge[i];
          if (!src.approved(t)) {
              src.registerToken(t);
              console.log("Registered token:", t);
          } else {
              console.log("Already registered:", t);
          }
      }

      console.log("\n=== Source Deployment Done ===");
      console.log("Save Source contract at:", address(src));
  }

  function _deployDestination(address admin) internal {
      console.log("\n=== Deploying Destination on BSC Testnet ===");
      Destination dst = new Destination(admin);
      console.log("Destination address:", address(dst));

      console.log("\n=== Creating Wrapped Tokens ===");
      for (uint i = 0; i < tokensToBridge.length; i++) {
          address t = tokensToBridge[i];
          if (dst.wrapped_tokens(t) == address(0)) {
              string memory nm = string(abi.encodePacked("Bridged", vm.toString(i)));
              string memory sym = string(abi.encodePacked("B", vm.toString(i)));
              address w = dst.createToken(t, nm, sym);
              console.log("Wrapped for", t, "→", w);
          } else {
              console.log("Wrapped exists for:", t);
          }
      }

      console.log("\n=== Destination Deployment Done ===");
      console.log("Save Destination contract at:", address(dst));
  }

}

