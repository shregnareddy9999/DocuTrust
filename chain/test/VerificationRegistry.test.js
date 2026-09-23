const { expect } = require("chai");
const { anyValue } = require("@nomicfoundation/hardhat-chai-matchers/withArgs");

describe("VerificationRegistry", function () {
  async function deployRegistry() {
    const Registry = await ethers.getContractFactory("VerificationRegistry");
    const registry = await Registry.deploy();
    await registry.waitForDeployment();
    return registry;
  }

  it("deploys successfully", async function () {
    const registry = await deployRegistry();
    expect(await registry.getAddress()).to.be.properAddress;
  });

  it("records verification with the required event", async function () {
    const registry = await deployRegistry();

    const verificationRef = ethers.keccak256(
      ethers.toUtf8Bytes("11111111-1111-1111-1111-111111111111")
    );

    const eventDigest = ethers.sha256(
      ethers.toUtf8Bytes("verification:0:test-salt")
    );

    await expect(
      registry.recordVerification(verificationRef, eventDigest, 0)
    )
      .to.emit(registry, "VerificationRecorded")
      .withArgs(verificationRef, eventDigest, 0, anyValue);
  });

  it("accepts all five terminal outcome codes", async function () {
    const registry = await deployRegistry();

    for (let code = 0; code <= 4; code++) {
      const ref = ethers.keccak256(
        ethers.toUtf8Bytes(`verification-${code}`)
      );

      const digest = ethers.sha256(
        ethers.toUtf8Bytes(`digest-${code}`)
      );

      await expect(
        registry.recordVerification(ref, digest, code)
      ).to.emit(registry, "VerificationRecorded");
    }
  });

  it("is append-only and permits multiple records", async function () {
    const registry = await deployRegistry();

    const ref1 = ethers.keccak256(
      ethers.toUtf8Bytes("verification-1")
    );
    const ref2 = ethers.keccak256(
      ethers.toUtf8Bytes("verification-2")
    );

    const digest1 = ethers.sha256(
      ethers.toUtf8Bytes("digest-1")
    );
    const digest2 = ethers.sha256(
      ethers.toUtf8Bytes("digest-2")
    );

    await expect(
      registry.recordVerification(ref1, digest1, 0)
    ).to.emit(registry, "VerificationRecorded");

    await expect(
      registry.recordVerification(ref2, digest2, 1)
    ).to.emit(registry, "VerificationRecorded");
  });

  it("exposes only recordVerification", async function () {
    const registry = await deployRegistry();

    const functions = registry.interface.fragments
      .filter((fragment) => fragment.type === "function")
      .map((fragment) => fragment.name);

    expect(functions).to.deep.equal(["recordVerification"]);
  });

  it("contains no personal-data fields in the event", async function () {
    const registry = await deployRegistry();

    const event = registry.interface.fragments.find(
      (fragment) =>
        fragment.type === "event" &&
        fragment.name === "VerificationRecorded"
    );

    expect(event).to.not.equal(undefined);

    expect(
      event.inputs.map((input) => input.name)
    ).to.deep.equal([
      "verificationRef",
      "eventDigest",
      "outcomeCode",
      "recordedAt"
    ]);
  });
});
