import requests, json

url = "https://catntmobfcenkhkodnqv.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNhdG50bW9iZmNlbmtoa29kbnF2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTA3NjY0OCwiZXhwIjoyMDk0NjUyNjQ4fQ.CNs93M6NfmoFwOzf6i0KyrLAwOJtjzY8I9ENkqBesZI"
headers = {"apikey": key, "Authorization": f"Bearer {key}"}

r = requests.get(f"{url}/rest/v1/dataset_runs?select=id,wallet,label,status,stats,created_at&limit=5", headers=headers, timeout=10)
for run in r.json():
    print(f"Run: {run['id'][:8]}... | {run['label']} | {run['status']} | {run['created_at']}")
    print(f"  Stats: {json.dumps(run['stats'])}")

r2 = requests.get(f"{url}/rest/v1/dataset_artifacts?select=artifact_type,file_name,row_count,sha256&limit=10", headers=headers, timeout=10)
for a in r2.json():
    print(f"  Artifact: {a['artifact_type']} | {a['file_name']} | {a['row_count']} rows")
