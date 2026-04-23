import { useAuction } from './context/Auctioncontext'
import LoginPage from './pages/Loginpage'
import AdminPage from './pages/Adminpage'
import BuyerPage from './pages/Buyerpage'


export default function App() {
  const { currentUser } = useAuction()

  if (!currentUser) return <LoginPage />
  if (currentUser.isAdmin) return <AdminPage />
  return <BuyerPage />
}