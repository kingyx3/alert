const spm = "a2o42.pdp_revamp.main_page.bottom_bar_main_button";
const quantity = Number(process.env.LAZADA_QUANTITY || "1");
const cookie = process.env.LAZADA_COOKIE;
const rawPairs = process.env.LAZADA_ITEM_SKU_PAIRS || "";

if (!cookie) {
  console.error("LAZADA_COOKIE is not set. Add it as a GitHub Actions repository secret.");
  process.exit(2);
}

if (!Number.isInteger(quantity) || quantity < 1) {
  console.error(`Invalid LAZADA_QUANTITY: ${process.env.LAZADA_QUANTITY}`);
  process.exit(2);
}

let pairs;
try {
  pairs = JSON.parse(rawPairs);
} catch {
  console.error(
    'LAZADA_ITEM_SKU_PAIRS must be valid JSON, e.g. [["13822368851","124830542173"]].',
  );
  process.exit(2);
}

if (
  !Array.isArray(pairs) ||
  pairs.length === 0 ||
  !pairs.every(
    (pair) =>
      Array.isArray(pair) &&
      pair.length === 2 &&
      String(pair[0]).trim() !== "" &&
      String(pair[1]).trim() !== "",
  )
) {
  console.error(
    "LAZADA_ITEM_SKU_PAIRS must be a non-empty JSON array of [itemId, skuId] pairs.",
  );
  process.exit(2);
}

class StopBatchError extends Error {}

async function postPair(itemId, skuId) {
  const url = new URL("https://checkout.lazada.sg/shipping");
  url.searchParams.set("spm", spm);

  const buyParams = JSON.stringify({
    items: [
      {
        itemId: String(itemId),
        skuId: String(skuId),
        quantity,
        attributes: null,
      },
    ],
  });

  const body = new URLSearchParams({ spm, buyParams });
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30_000);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9,en-SG;q=0.8",
        "content-type": "application/x-www-form-urlencoded",
        cookie,
        origin: "https://www.lazada.sg",
        referer: "https://www.lazada.sg/",
        // Do not impersonate a browser fingerprint. Identify this as repo automation.
        "user-agent": "kingyx3-alert-lazada-checkout/1.0 (GitHub Actions)",
      },
      body,
      redirect: "follow",
      signal: controller.signal,
    });

    const text = await response.text();
    const lower = text.toLowerCase();
    const challenge = [
      "captcha",
      "unusual traffic",
      "security verification",
      "verify you are human",
      "punish",
    ].some((marker) => lower.includes(marker));
    const redirectedToLogin = /\/login(?:[/?#]|$)/i.test(response.url);
    const rateLimited = response.status === 429 || response.status === 403;

    console.log(
      JSON.stringify(
        {
          timestamp: new Date().toISOString(),
          itemId: String(itemId),
          skuId: String(skuId),
          quantity,
          status: response.status,
          ok: response.ok,
          finalUrl: response.url,
          responseBytes: Buffer.byteLength(text),
          challenge,
          redirectedToLogin,
          rateLimited,
        },
        null,
        2,
      ),
    );

    if (challenge || redirectedToLogin || rateLimited) {
      throw new StopBatchError(
        `Stopping batch: Lazada returned a challenge, login redirect, or rate-limit response for item=${itemId}, sku=${skuId}.`,
      );
    }

    if (!response.ok) {
      throw new Error(
        `Lazada shipping POST returned HTTP ${response.status} for item=${itemId}, sku=${skuId}.`,
      );
    }
  } finally {
    clearTimeout(timeout);
  }
}

let failed = false;

for (const [itemId, skuId] of pairs) {
  try {
    await postPair(String(itemId), String(skuId));
  } catch (error) {
    failed = true;

    if (error?.name === "AbortError") {
      console.error(`POST timed out for item=${itemId}, sku=${skuId}`);
    } else {
      console.error(
        `POST failed for item=${itemId}, sku=${skuId}:`,
        error?.message || error,
      );
    }

    // Never keep probing when Lazada asks for verification, authentication,
    // or indicates rate limiting. The next scheduled run can try again later.
    if (error instanceof StopBatchError) {
      break;
    }
  }
}

if (failed) {
  process.exit(1);
}
