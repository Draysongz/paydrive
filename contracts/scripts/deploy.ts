import { ethers } from "hardhat";

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying with:", deployer.address);

  // Deploy SimpleVault
  const SimpleVault = await ethers.getContractFactory("SimpleVault");
  const simpleVault = await SimpleVault.deploy();
  await simpleVault.waitForDeployment();
  const simpleAddr = await simpleVault.getAddress();
  console.log("SimpleVault deployed to:", simpleAddr);

  // Deploy MultiSigVault (2-of-3 with deployer as one signer)
  // For demo: deployer is both signer[0] and the agent
  const signers = [deployer.address];
  const threshold = 1; // 1-of-1 for demo; change for production
  const MultiSigVault = await ethers.getContractFactory("MultiSigVault");
  const multiSigVault = await MultiSigVault.deploy(signers, threshold);
  await multiSigVault.waitForDeployment();
  const multiAddr = await multiSigVault.getAddress();
  console.log("MultiSigVault deployed to:", multiAddr);

  console.log("\nAdd to .env:");
  console.log(`SIMPLE_VAULT_ADDRESS=${simpleAddr}`);
  console.log(`MULTISIG_VAULT_ADDRESS=${multiAddr}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
