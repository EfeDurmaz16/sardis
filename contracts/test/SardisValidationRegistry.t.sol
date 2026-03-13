// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/SardisValidationRegistry.sol";
import "../src/SardisIdentityRegistry.sol";
import "../src/interfaces/IValidationRegistry.sol";

contract SardisValidationRegistryTest is Test {
    SardisIdentityRegistry internal identity;
    SardisValidationRegistry internal validation;

    address internal agentOwner = address(0xA11CE);
    address internal validator1 = address(0xAA01);
    address internal validator2 = address(0xAA02);
    address internal stranger = address(0x999);

    uint256 internal agentId;

    function setUp() public {
        identity = new SardisIdentityRegistry();
        validation = new SardisValidationRegistry(address(identity));

        vm.prank(agentOwner);
        agentId = identity.register("https://agent.example.com");
    }

    // ============ getIdentityRegistry ============

    function testGetIdentityRegistry() public view {
        assertEq(validation.getIdentityRegistry(), address(identity));
    }

    // ============ Constructor ============

    function testConstructorRevertsZeroAddress() public {
        vm.expectRevert(SardisValidationRegistry.ZeroAddress.selector);
        new SardisValidationRegistry(address(0));
    }

    // ============ validationRequest ============

    function testValidationRequest() public {
        bytes32 reqHash = keccak256("req1");

        vm.prank(agentOwner);
        validation.validationRequest(validator1, agentId, "https://req.com", reqHash);

        (address v, uint256 aid, uint8 resp,,, uint256 lastUpdate) = validation.getValidationStatus(reqHash);
        assertEq(v, validator1);
        assertEq(aid, agentId);
        assertEq(resp, 0);
        assertEq(lastUpdate, 0); // lastUpdate only set when validator responds
    }

    function testValidationRequestRevertsNotOwner() public {
        vm.prank(stranger);
        vm.expectRevert(SardisValidationRegistry.NotAgentOwnerOrApproved.selector);
        validation.validationRequest(validator1, agentId, "uri", keccak256("x"));
    }

    function testValidationRequestRevertsNonexistentAgent() public {
        vm.prank(agentOwner);
        vm.expectRevert(SardisValidationRegistry.AgentDoesNotExist.selector);
        validation.validationRequest(validator1, 999, "uri", keccak256("x"));
    }

    function testValidationRequestRevertsZeroValidator() public {
        vm.prank(agentOwner);
        vm.expectRevert(SardisValidationRegistry.ZeroAddress.selector);
        validation.validationRequest(address(0), agentId, "uri", keccak256("x"));
    }

    function testValidationRequestRevertsDuplicate() public {
        bytes32 reqHash = keccak256("req1");

        vm.startPrank(agentOwner);
        validation.validationRequest(validator1, agentId, "uri", reqHash);

        vm.expectRevert(SardisValidationRegistry.RequestAlreadyExists.selector);
        validation.validationRequest(validator1, agentId, "uri2", reqHash);
        vm.stopPrank();
    }

    function testValidationRequestEmitsEvent() public {
        bytes32 reqHash = keccak256("req1");

        vm.prank(agentOwner);
        vm.expectEmit(true, true, true, true);
        emit IValidationRegistry.ValidationRequest(validator1, agentId, "https://req.com", reqHash);
        validation.validationRequest(validator1, agentId, "https://req.com", reqHash);
    }

    function testApprovedOperatorCanRequest() public {
        vm.prank(agentOwner);
        identity.approve(stranger, agentId);

        vm.prank(stranger);
        validation.validationRequest(validator1, agentId, "uri", keccak256("x"));
    }

    // ============ validationResponse ============

    function testValidationResponse() public {
        bytes32 reqHash = keccak256("req1");

        vm.prank(agentOwner);
        validation.validationRequest(validator1, agentId, "uri", reqHash);

        vm.prank(validator1);
        validation.validationResponse(reqHash, 85, "https://resp.com", keccak256("resp"), "security");

        (,, uint8 resp, bytes32 respHash, string memory tag, uint256 lastUpdate) =
            validation.getValidationStatus(reqHash);
        assertEq(resp, 85);
        assertEq(respHash, keccak256("resp"));
        assertEq(tag, "security");
        assertGt(lastUpdate, 0);
    }

    function testValidationResponseUpdate() public {
        bytes32 reqHash = keccak256("req1");

        vm.prank(agentOwner);
        validation.validationRequest(validator1, agentId, "uri", reqHash);

        vm.startPrank(validator1);
        validation.validationResponse(reqHash, 50, "", bytes32(0), "initial");
        validation.validationResponse(reqHash, 90, "", bytes32(0), "updated");
        vm.stopPrank();

        (,, uint8 resp,, string memory tag,) = validation.getValidationStatus(reqHash);
        assertEq(resp, 90);
        assertEq(tag, "updated");
    }

    function testValidationResponseRevertsNotValidator() public {
        bytes32 reqHash = keccak256("req1");

        vm.prank(agentOwner);
        validation.validationRequest(validator1, agentId, "uri", reqHash);

        vm.prank(stranger);
        vm.expectRevert(SardisValidationRegistry.NotDesignatedValidator.selector);
        validation.validationResponse(reqHash, 80, "", bytes32(0), "");
    }

    function testValidationResponseRevertsInvalidScore() public {
        bytes32 reqHash = keccak256("req1");

        vm.prank(agentOwner);
        validation.validationRequest(validator1, agentId, "uri", reqHash);

        vm.prank(validator1);
        vm.expectRevert(SardisValidationRegistry.InvalidResponse.selector);
        validation.validationResponse(reqHash, 101, "", bytes32(0), "");
    }

    function testValidationResponseRevertsNonexistent() public {
        vm.prank(validator1);
        vm.expectRevert(SardisValidationRegistry.RequestDoesNotExist.selector);
        validation.validationResponse(keccak256("nope"), 80, "", bytes32(0), "");
    }

    function testValidationResponseEmitsEvent() public {
        bytes32 reqHash = keccak256("req1");

        vm.prank(agentOwner);
        validation.validationRequest(validator1, agentId, "uri", reqHash);

        vm.prank(validator1);
        vm.expectEmit(true, true, true, true);
        emit IValidationRegistry.ValidationResponse(
            validator1, agentId, reqHash, 85, "https://resp.com", keccak256("r"), "security"
        );
        validation.validationResponse(reqHash, 85, "https://resp.com", keccak256("r"), "security");
    }

    // ============ getSummary ============

    function testGetSummaryBasic() public {
        bytes32 req1 = keccak256("req1");
        bytes32 req2 = keccak256("req2");

        vm.startPrank(agentOwner);
        validation.validationRequest(validator1, agentId, "uri1", req1);
        validation.validationRequest(validator2, agentId, "uri2", req2);
        vm.stopPrank();

        vm.prank(validator1);
        validation.validationResponse(req1, 80, "", bytes32(0), "");
        vm.prank(validator2);
        validation.validationResponse(req2, 60, "", bytes32(0), "");

        address[] memory validators = new address[](0);
        (uint64 count, uint8 avg) = validation.getSummary(agentId, validators, "");
        assertEq(count, 2);
        assertEq(avg, 70); // (80+60)/2
    }

    function testGetSummaryFilterByValidator() public {
        bytes32 req1 = keccak256("req1");
        bytes32 req2 = keccak256("req2");

        vm.startPrank(agentOwner);
        validation.validationRequest(validator1, agentId, "uri1", req1);
        validation.validationRequest(validator2, agentId, "uri2", req2);
        vm.stopPrank();

        vm.prank(validator1);
        validation.validationResponse(req1, 80, "", bytes32(0), "");
        vm.prank(validator2);
        validation.validationResponse(req2, 60, "", bytes32(0), "");

        address[] memory validators = new address[](1);
        validators[0] = validator1;
        (uint64 count, uint8 avg) = validation.getSummary(agentId, validators, "");
        assertEq(count, 1);
        assertEq(avg, 80);
    }

    function testGetSummaryFilterByTag() public {
        bytes32 req1 = keccak256("req1");
        bytes32 req2 = keccak256("req2");

        vm.startPrank(agentOwner);
        validation.validationRequest(validator1, agentId, "uri1", req1);
        validation.validationRequest(validator1, agentId, "uri2", req2);
        vm.stopPrank();

        vm.startPrank(validator1);
        validation.validationResponse(req1, 80, "", bytes32(0), "security");
        validation.validationResponse(req2, 60, "", bytes32(0), "accuracy");
        vm.stopPrank();

        address[] memory validators = new address[](0);
        (uint64 count, uint8 avg) = validation.getSummary(agentId, validators, "security");
        assertEq(count, 1);
        assertEq(avg, 80);
    }

    // ============ getAgentValidations ============

    function testGetAgentValidations() public {
        bytes32 req1 = keccak256("req1");
        bytes32 req2 = keccak256("req2");

        vm.startPrank(agentOwner);
        validation.validationRequest(validator1, agentId, "uri1", req1);
        validation.validationRequest(validator2, agentId, "uri2", req2);
        vm.stopPrank();

        bytes32[] memory hashes = validation.getAgentValidations(agentId);
        assertEq(hashes.length, 2);
        assertEq(hashes[0], req1);
        assertEq(hashes[1], req2);
    }

    // ============ getValidatorRequests ============

    function testGetValidatorRequests() public {
        bytes32 req1 = keccak256("req1");

        vm.prank(agentOwner);
        validation.validationRequest(validator1, agentId, "uri1", req1);

        bytes32[] memory hashes = validation.getValidatorRequests(validator1);
        assertEq(hashes.length, 1);
        assertEq(hashes[0], req1);
    }
}
