import fs from "node:fs";

export const REQUIRED_DEPLOY_SECRETS = [
  "TELEGRAM_BOT_TOKEN",
  "TELEGRAM_CHANNEL_ID",
  "DEBUG_TOKEN",
];

export const OPTIONAL_DEPLOY_SECRETS = [
  "TCG_API_KEY",
  "PRICECHARTING_TOKEN",
  "X_BEARER_TOKEN",
  "INGEST_TOKEN",
];

export function collectDeploySecrets(env = process.env) {
  const missing = REQUIRED_DEPLOY_SECRETS.filter((name) => !String(env[name] || "").trim());
  if (missing.length) {
    throw new Error(`Missing required deploy secrets/variables: ${missing.join(", ")}`);
  }

  const names = [...REQUIRED_DEPLOY_SECRETS, ...OPTIONAL_DEPLOY_SECRETS];
  return Object.fromEntries(
    names
      .filter((name) => String(env[name] || "").length > 0)
      .map((name) => [name, String(env[name])]),
  );
}

export function writeDeploySecrets(filePath, env = process.env) {
  if (!filePath) throw new Error("Output path is required");
  const secrets = collectDeploySecrets(env);
  fs.writeFileSync(filePath, `${JSON.stringify(secrets)}\n`, { encoding: "utf8", mode: 0o600 });
  fs.chmodSync(filePath, 0o600);
  return Object.keys(secrets);
}

if (process.argv[1]?.endsWith("write-deploy-secrets.mjs")) {
  const filePath = process.argv[2] || ".deploy-secrets.json";
  const names = writeDeploySecrets(filePath);
  console.log(`Prepared Cloudflare secrets file with: ${names.join(", ")}`);
}
