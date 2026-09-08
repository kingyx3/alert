export async function loadSnapshot(state) {
  const [meta, sourceStates, opportunities, alerts, marketCache] = await Promise.all([
    state.storage.get("meta"),
    state.storage.get("sourceStates"),
    state.storage.get("opportunities"),
    state.storage.get("alerts"),
    state.storage.get("marketCache"),
  ]);
  return {
    meta: meta || { recentEvents: [], lastCheckAt: null, lastSuccessAt: null, consecutiveFailures: 0 },
    sourceStates: sourceStates || {},
    opportunities: opportunities || [],
    alerts: alerts || {},
    marketCache: marketCache || {},
    marketLookupsThisRun: 0,
    marketBudgetExhausted: false,
  };
}

export async function persistSnapshot(state, data) {
  await state.storage.put(data);
}
