const hre = require("hardhat");

async function main() {
  const Registry = await hre.ethers.getContractFactory(
    "VerificationRegistry"
  );

  const registry = await Registry.deploy();
  await registry.waitForDeployment();

  const address = await registry.getAddress();

  console.log("VerificationRegistry deployed to:", address);

  const network = await hre.ethers.provider.getNetwork();
  console.log("Chain ID:", network.chainId.toString());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
