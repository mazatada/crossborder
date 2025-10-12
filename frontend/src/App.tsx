import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import HS from "./pages/HS"; import PN from "./pages/PN"; import Pack from "./pages/Pack";
import { AppBar, Toolbar, Button, Container } from "@mui/material";

export default function App(){
  return (
    <BrowserRouter>
      <AppBar position="static"><Toolbar>
        <Button color="inherit" component={Link} to="/hs">HS</Button>
        <Button color="inherit" component={Link} to="/pn">PN</Button>
        <Button color="inherit" component={Link} to="/pack">Pack</Button>
      </Toolbar></AppBar>
      <Container maxWidth="lg" sx={{mt:2}}>
        <Routes>
          <Route path="/hs" element={<HS/>}/>
          <Route path="/pn" element={<PN/>}/>
          <Route path="/pack" element={<Pack/>}/>
          <Route path="*" element={<HS/>}/>
        </Routes>
      </Container>
    </BrowserRouter>
  );
}
