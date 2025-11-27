require("dotenv").config();
const { createClient } = require("@supabase/supabase-js");

function requireEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing environment variable: ${name}`);
  }
  return value;
}

async function main() {
  const url = requireEnv("SUPABASE_URL");
  const key = requireEnv("SUPABASE_KEY");

  const supabase = createClient(url, key);
  const { data, error } = await supabase.from("chat_messages").select("*").limit(5);
  if (error) {
    throw error;
  }
  console.log(data ?? []);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
