import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
// AUTH DISABLED -- uncomment below to re-enable login/signup
// import { GoogleOAuthProvider } from '@react-oauth/google'
// import { AuthProvider } from './auth/AuthContext'
import './index.css'
import App from './App.jsx'

// const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {/* AUTH DISABLED -- restore GoogleOAuthProvider + AuthProvider to re-enable */}
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)

// ORIGINAL (with auth):
// createRoot(document.getElementById('root')).render(
//   <StrictMode>
//     <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
//       <BrowserRouter>
//         <AuthProvider>
//           <App />
//         </AuthProvider>
//       </BrowserRouter>
//     </GoogleOAuthProvider>
//   </StrictMode>,
// )
