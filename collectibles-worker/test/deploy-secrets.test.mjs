import test from "node:test";
import assert from "node:assert/strict";
import { collectDeploySecrets, OPTIONAL_DEPLOY_SECRETS, REQUIRED_DEPLOY_SECRETS } from "../scripts/write-deploy-secrets.mjs";

function baseEnv() {
  return {
    TELEGRAM_BOT_TOKEN: "telegram-token",
    TELEGRAM_CHANNEL_ID: "channel-id",
    DEBUG_TOKEN: "debug-token",
  };
}

test("deploy secret builder requires core Worker secrets", () => {
  assert.throws(
    () => collectDeploySecrets({ TELEGRAM_BOT_TOKEN: "telegram-token" }),
    /TELEGRAM_CHANNEL_ID, DEBUG_TOKEN/,
  );
});

test("deploy secret builder skips unset optional provider secrets", () => {
  const secrets = collectDeploySecrets(baseEnv());
  assert.deepEqual(Object.keys(secrets).sort(), [...REQUIRED_DEPLOY_SECRETS].sort());
  for (const name of OPTIONAL_DEPLOY_SECRETS) assert.equal(name in secrets, false);
});

test("deploy secret builder includes configured optional provider secrets", () => {
  const secrets = collectDeploySecrets({
    ...baseEnv(),
    TCG_API_KEY: "tcg_live_test",
    PRICECHARTING_TOKEN: "pc-test",
    X_BEARER_TOKEN: "x-test",
    INSTAGRAM_API_KEY: "ig-live-test",
    INSTAGRAM_ACCOUNTS_JSON: '[{"username":"shop"}]',
    INGEST_TOKEN: "ingest-test",
  });

  assert.equal(secrets.TCG_API_KEY, "tcg_live_test");
  assert.equal(secrets.PRICECHARTING_TOKEN, "pc-test");
  assert.equal(secrets.X_BEARER_TOKEN, "x-test");
  assert.equal(secrets.INSTAGRAM_API_KEY, "ig-live-test");
  assert.equal(secrets.INSTAGRAM_ACCOUNTS_JSON, '[{"username":"shop"}]');
  assert.equal(secrets.INGEST_TOKEN, "ingest-test");
});
