import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import * as dotenv from "dotenv";

dotenv.config({ path: "../.env" });

const config: HardhatUserConfig = {
  solidity: "0.8.24",
  paths: {
    sources: "./",
    artifacts: "./artifacts",
    cache: "./cache",
  },
  networks: {
    hardhat: {},
    localhost: {
      url: "http://127.0.0.1:8545",
    },
    baseSepolia: {
      url: process.env.WEB3_RPC_URL || "https://sepolia.base.org",
      accounts: process.env.WEB3_PRIVATE_KEY ? [process.env.WEB3_PRIVATE_KEY] : [],
      chainId: 84532,
    },
  },
};

export default config;
