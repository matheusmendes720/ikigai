const RUN_ID = process.argv[2];
const NODE_ID = process.argv[3];
const MESSAGE = process.argv[4];

if (!RUN_ID || !NODE_ID || !MESSAGE) {
  console.error('usage: node repair.js <run_id> <node_id> <message>');
  process.exit(2);
}

(async () => {
  const res = await tool.workflow({
    action: 'send',
    run_id: RUN_ID,
    node_id: NODE_ID,
    message: MESSAGE,
  });
  console.log(JSON.stringify(res).slice(0, 1500));
})();
