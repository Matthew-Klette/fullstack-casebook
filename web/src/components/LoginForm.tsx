import { useState, type FormEvent } from "react";
import { ApiError } from "../api/client";
import { useLogin } from "../api/hooks";

export function LoginForm() {
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    login.mutate({ email, password });
  };

  return (
    <main className="card narrow">
      <h1>Shiftboard</h1>
      <form onSubmit={submit}>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <button type="submit" disabled={login.isPending}>
          Sign in
        </button>
        {login.error && (
          <p role="alert" className="error">
            {login.error instanceof ApiError && login.error.status === 401
              ? "Email or password is incorrect."
              : "Could not sign in. Try again."}
          </p>
        )}
      </form>
    </main>
  );
}
