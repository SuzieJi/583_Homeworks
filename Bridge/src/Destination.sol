// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";

contract Destination is AccessControl {
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
    bytes32 public constant CREATOR_ROLE = keccak256("CREATOR_ROLE");
	mapping( address => address) public underlying_tokens;
	mapping( address => address) public wrapped_tokens;
	address[] public tokens;

	event Creation( address indexed underlying_token, address indexed wrapped_token );
	event Wrap( address indexed underlying_token, address indexed wrapped_token, address indexed to, uint256 amount );
	event Unwrap( address indexed underlying_token, address indexed wrapped_token, address frm, address indexed to, uint256 amount );

    constructor( address admin ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CREATOR_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
    }

	function wrap(address _underlying_token, address _recipient, uint256 _amount ) public onlyRole(WARDEN_ROLE) {
		//YOUR CODE HERE
    address wrapped = wrapped_tokens[_underlying_token];
		require(wrapped != address(0), "Destination: asset not registered");
		BridgeToken(wrapped).mint(_recipient, _amount);
		emit Wrap(_underlying_token, wrapped, _recipient, _amount);
	}

	function unwrap(address _wrapped_token, address _recipient, uint256 _amount ) public {
		//YOUR CODE HERE
		address underlying = underlying_tokens[_wrapped_token];
		require(underlying != address(0), "Destination: token not recognized");
		BridgeToken(_wrapped_token).clawBack(msg.sender, _amount);
		emit Unwrap(underlying, _wrapped_token, msg.sender, _recipient, _amount);
	}

	function createToken(address _underlying_token, string memory name, string memory symbol ) public onlyRole(CREATOR_ROLE) returns(address) {
		//YOUR CODE HERE
		require(_underlying_token != address(0), "Destination: zero underlying");
		require(wrapped_tokens[_underlying_token] == address(0), "Destination: already created");
		BridgeToken token = new BridgeToken(_underlying_token, name, symbol, address(this));
		address newWrapped = address(token);
		wrapped_tokens[_underlying_token] = newWrapped;
		underlying_tokens[newWrapped] = _underlying_token;
		tokens.push(newWrapped);
		emit Creation(_underlying_token, newWrapped);
		return newWrapped;
	}

}

