import { useMe } from "./api/hooks";
import { Board } from "./components/Board";
import { LoginForm } from "./components/LoginForm";

export function App() {
  const me = useMe();
  if (me.isPending) return <main className="card narrow">Loading</main>;
  if (!me.data) return <LoginForm />;
  return <Board user={me.data} />;
}
