const express = require('express');
const path = require('path');
const cors = require('cors');
const compression = require('compression');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(compression());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Mock database of cracks/releases
const releases = [
  {
    id: "neverlose-v3-crack",
    title: "Neverlose CS2 Build",
    category: "cs2",
    version: "v3.1.4 (Pre-Beta)",
    author: "AnonGrief Reversing Team",
    date: "2026-10-02",
    status: "undetected", // undetected, updating, testing, detected
    game: "Counter-Strike 2",
    rating: 4.9,
    downloads: 14820,
    tags: ["Ragebot", "Anti-Aim", "Lua Loader", "Inventory Changer"],
    description: "Fully decoupled client library with patched license verification routines. Includes cloud configs and resolved Lua VM sandbox.",
    features: [
      "Bypass integrity check on client.dll",
      "Dynamic anti-aim with jitter & manual override",
      "Auto-peek with visual backtrack indicator",
      "Full Lua engine with unlimited script support",
      "Direct sound ESP & grenade prediction"
    ],
    hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    downloadUrl: "#download-modal",
    virustotalUrl: "https://www.virustotal.com"
  },
  {
    id: "fatality-win-crack",
    title: "Fatality.win Crack",
    category: "cs2",
    version: "v2.0.9",
    author: "0xGrief",
    date: "2026-09-28",
    status: "undetected",
    game: "Counter-Strike 2",
    rating: 4.8,
    downloads: 9410,
    tags: ["HvH Beast", "Resolver v2", "Doubletap", "Rapid Fire"],
    description: "Legendary HvH internal rebuild. Clean injection without external dependencies or telemetry hooks.",
    features: [
      "Signature resolver with brute force logic",
      "Sub-tick doubletap optimization",
      "Adaptive weapons damage override",
      "Sleek customizable ImGui interface",
      "Instant weapon switch and teleport peek"
    ],
    hash: "a4f2c98d41e7790b14c3325672abef9092837261947264829104827361958273",
    downloadUrl: "#download-modal",
    virustotalUrl: "https://www.virustotal.com"
  },
  {
    id: "celestial-recode-minecraft",
    title: "Celestial Recode 1.20+",
    category: "minecraft",
    version: "v4.5.1",
    author: "Krypton & AnonGrief",
    date: "2026-10-01",
    status: "undetected",
    game: "Minecraft (Fabric / Forge)",
    rating: 4.95,
    downloads: 32900,
    tags: ["Aura", "Flight", "Bypass GrimAC", "Matrix 7"],
    description: "Clean JAR client with dismantled HWID authorization and bypassed packet limiters for top Russian and EU anarchy servers (ReallyWorld, FunTime, HolyWorld).",
    features: [
      "Full GrimAC and Matrix anti-cheat disablers",
      "TargetESP, FreeCam, ChinaHat & customizable shaders",
      "AutoTotem with inventory synchronization",
      "AirJump, LongJump and ElytraFly bypasses",
      "Built-in Macro, Baritone AI integration"
    ],
    hash: "74b62f558197f26487e671239854728919246193857192847192847192847192",
    downloadUrl: "#download-modal",
    virustotalUrl: "https://www.virustotal.com"
  },
  {
    id: "akrien-premium-crack",
    title: "Akrien AntiCheat Bypass",
    category: "minecraft",
    version: "v12.2 Premium",
    author: "AnonGrief",
    date: "2026-09-25",
    status: "undetected",
    game: "Minecraft 1.12.2 - 1.16.5",
    rating: 4.7,
    downloads: 18240,
    tags: ["Ghost", "Legit", "Killaura", "AutoArmor"],
    description: "Patched launcher and offline token injector. Bypasses client-side scan utilities with zero footprint.",
    features: [
      "Undetected on screen-shares (Process Hider included)",
      "Legit Aimbot with customizable FOV & smoothing",
      "Silent Aim and trigger bot",
      "Clean UI styled after modern Spotify dark theme"
    ],
    hash: "9823749817294871928471928471928471928471928471928471928471928471",
    downloadUrl: "#download-modal",
    virustotalUrl: "https://www.virustotal.com"
  },
  {
    id: "midnight-cs2-leak",
    title: "Midnight CS2 Legit/Semi",
    category: "cs2",
    version: "v4.0.0",
    author: "NullByte",
    date: "2026-09-30",
    status: "undetected",
    game: "Counter-Strike 2",
    rating: 4.9,
    downloads: 27500,
    tags: ["Legit", "Cloud Radar", "Skinchanger", "OBS Proof"],
    description: "The cleanest CS2 legit software archive. All cloud features routed through local mock proxy.",
    features: [
      "Bypass OBS & Discord capture (Stream Proof)",
      "Dynamic Recoil Control System (RCS)",
      "Web radar for second monitor or phone",
      "Instant skin and knife sync without lag"
    ],
    hash: "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    downloadUrl: "#download-modal",
    virustotalUrl: "https://www.virustotal.com"
  },
  {
    id: "eulen-fivem-bypass",
    title: "Eulen GTA V / FiveM",
    category: "fivem",
    version: "v5.8.3",
    author: "AnonGrief",
    date: "2026-10-01",
    status: "testing",
    game: "GTA V & FiveM",
    rating: 4.6,
    downloads: 11200,
    tags: ["FiveM", "Executor", "Lua Dumper", "Aimbot"],
    description: "Bypasses server side anti-cheats (FiveGuard, Phoenix, Wave). Includes Lua script executor and visual overlay.",
    features: [
      "Custom Lua executor with resource bypass",
      "Server cache dumper and weapon spawner",
      "Player ESP, Godmode, NoClip, Teleport",
      "Triggerbot and silent aim with bone selection"
    ],
    hash: "fedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321",
    downloadUrl: "#download-modal",
    virustotalUrl: "https://www.virustotal.com"
  },
  {
    id: "rust-recoil-script-suite",
    title: "Rust Script Engine Pro",
    category: "rust",
    version: "v2.6",
    author: "0xGrief",
    date: "2026-09-29",
    status: "undetected",
    game: "Rust",
    rating: 4.85,
    downloads: 15300,
    tags: ["EAC Safe", "Hardware Emulation", "Recoil", "Crosshair"],
    description: "Undetected hardware mouse event generator. Works at low-level driver tier, invisible to EasyAntiCheat scan loops.",
    features: [
      "Humanized recoil pattern curves",
      "Automatic weapon and attachment detection",
      "Zero game memory read/write (100% External)",
      "Support for all resolutions and FOVs"
    ],
    hash: "654321fedcba0987654321fedcba0987654321fedcba0987654321fedcba0987",
    downloadUrl: "#download-modal",
    virustotalUrl: "https://www.virustotal.com"
  },
  {
    id: "anongrief-multiloader",
    title: "AnonGrief Universal Loader",
    category: "tools",
    version: "v3.0.0",
    author: "AnonGrief Core Devs",
    date: "2026-10-03",
    status: "undetected",
    game: "Multi-Game Hub",
    rating: 5.0,
    downloads: 54100,
    tags: ["One-Click", "Cloud Sync", "Auto-Inject", "HWID Spoofer"],
    description: "The core master loader for all AnonGrief crack modules. Automated driver loading, memory protection and real-time updates.",
    features: [
      "Kernel manual map injection engine",
      "Built-in temporary HWID Spoofer (NIC, Disk, SMBIOS)",
      "Encrypted RAM payload delivery",
      "Zero traces in registry or prefetch"
    ],
    hash: "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff",
    downloadUrl: "#download-modal",
    virustotalUrl: "https://www.virustotal.com"
  }
];

// API Endpoints
app.get('/api/releases', (req, res) => {
  const { category, search } = req.query;
  let filtered = [...releases];

  if (category && category !== 'all') {
    filtered = filtered.filter(item => item.category === category);
  }

  if (search) {
    const q = search.toLowerCase();
    filtered = filtered.filter(item => 
      item.title.toLowerCase().includes(q) ||
      item.game.toLowerCase().includes(q) ||
      item.tags.some(t => t.toLowerCase().includes(q)) ||
      item.description.toLowerCase().includes(q)
    );
  }

  res.json({
    success: true,
    count: filtered.length,
    data: filtered
  });
});

app.get('/api/releases/:id', (req, res) => {
  const release = releases.find(r => r.id === req.params.id);
  if (!release) {
    return res.status(404).json({ success: false, error: 'Release not found' });
  }
  res.json({ success: true, data: release });
});

app.get('/api/stats', (req, res) => {
  const totalDownloads = releases.reduce((acc, r) => acc + r.downloads, 0);
  res.json({
    success: true,
    stats: {
      totalReleases: releases.length,
      totalDownloads: totalDownloads + 41290, // Include loader base count
      activeUsers: 842,
      uptime: "99.98%",
      serverStatus: "ONLINE",
      version: "3.2.0-PROD"
    }
  });
});

// Fallback to SPA
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[AnonGrief] Server running on port ${PORT}`);
});
