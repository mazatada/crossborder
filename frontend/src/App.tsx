import { Box, Container, Tab, Tabs } from "@mui/material";
import { useEffect, useState } from "react";
import HSPage from "./pages/HSPage";
import PackPage from "./pages/PackPage";
import PNPage from "./pages/PNPage";

export default function App() {
	const [tab, setTab] = useState(0);
	const [health, setHealth] = useState("checking...");
	useEffect(() => {
		fetch(`${import.meta.env.VITE_API_BASE}/v1/health`)
			.then((r) => r.json())
			.then((j) => setHealth(`status=${j.status}`))
			.catch(() => setHealth("failed"));
	}, []);
	return (
		<Container sx={{ py: 3 }}>
			<Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 1 }}>
				<Tab label="HS" />
				<Tab label="Pack" />
				<Tab label="PN" />
			</Tabs>
			<Box sx={{ mb: 2, fontSize: 13, color: "text.secondary" }}>
				Backend health: {health}
			</Box>
			<Box role="tabpanel" hidden={tab !== 0}>
				<HSPage />
			</Box>
			<Box role="tabpanel" hidden={tab !== 1}>
				<PackPage />
			</Box>
			<Box role="tabpanel" hidden={tab !== 2}>
				<PNPage />
			</Box>
		</Container>
	);
}
