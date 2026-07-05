async function loadUsers() {
  const res = await fetch("/api/search?q=widgets");
  return res.json();
}
const client = { get: (u) => fetch(u) };
axios.get('/api/users');
const ignored = fetch(`/api/${dynamicSegment}/x`);
