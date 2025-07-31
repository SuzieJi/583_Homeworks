// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "forge-std/Script.sol";
import "forge-std/console.sol";
import "../src/Source.sol";
import "../src/Destination.sol";

contract DeployBridgeContracts is Script {

    address[] public tokenList = [
        0xc677c31AD31F73A5290f5ef067F8CEF8d301e45c,
        0x0773b81e0524447784CcE1F3808fed6AaA156eC8
    ];

    function run() external {
        uint256 key = vm.envUint("PRIVATE_KEY");
        address sender = vm.addr(key);

        console.log("Using address:", sender);
        console.log("Running on chain ID:", block.chainid);

        vm.startBroadcast(key);

        if (block.chainid == 43113) {
            deploySource(sender);
        } else if (block.chainid == 97) {
            deployDestination(sender);
        } else {
            console.log("Unrecognized network:", block.chainid);
        }

        vm.stopBroadcast();
    }

    function deploySource(address owner) internal {
        console.log("\n>> Deploying Source contract on Avalanche Fuji...");

        Source src = new Source(owner);
        console.log("Source contract deployed at:", address(src));

        console.log("\n>> Registering tokens with Source...");
        for (uint i = 0; i < tokenList.length; i++) {
            address token = tokenList[i];

            if (!src.approved(token)) {
                src.registerToken(token);
                console.log("Registered token:", token);
            } else {
                console.log("Token already registered:", token);
            }
        }

        console.log("\nSource deployment finished.");
    }

    function deployDestination(address owner) internal {
        console.log("\n>> Deploying Destination contract on BSC Testnet...");

        Destination dst = new Destination(owner);
        console.log("Destination contract deployed at:", address(dst));

        console.log("\n>> Creating wrapped versions of tokens...");
        for (uint i = 0; i < tokenList.length; i++) {
            address originToken = tokenList[i];

            if (dst.wrapped_tokens(originToken) == address(0)) {
                string memory tokenName = string.concat("WrappedToken", vm.toString(i + 1));
                string memory tokenSymbol = string.concat("WT", vm.toString(i + 1));

                address wrapped = dst.createToken(originToken, tokenName, tokenSymbol);
                console.log("Created wrapped token for:", originToken);
                console.log("Wrapped token address:", wrapped);
            } else {
                console.log("Wrapped token already exists for:", originToken);
            }
        }

        console.log("\nDestination deployment finished.");
    }
}
