"use client";

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { login as apiLogin, fetchWithAuth } from "./api";

type User = {
	username: string;
	role: string;
	full_name: string;
};

type AuthContextType = {
	user: User | null;
	token: string | null;
	loading: boolean;
	login: (username: string, password: string) => Promise<void>;
	logout: () => void;
};

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
	const [user, setUser] = useState<User | null>(null);
	const [token, setToken] = useState<string | null>(null);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		const stored = localStorage.getItem("polimilpa_token");
		if (!stored) {
			setLoading(false);
			return;
		}
		setToken(stored);
		fetchWithAuth("/v1/auth/me", {}, stored)
			.then((res) => {
				if (!res.ok) throw new Error("token expired");
				return res.json() as Promise<User>;
			})
			.then((data) => setUser(data))
			.catch(() => {
				localStorage.removeItem("polimilpa_token");
				setToken(null);
			})
			.finally(() => setLoading(false));
	}, []);

	const login = useCallback(async (username: string, password: string) => {
		const data = await apiLogin(username, password);
		localStorage.setItem("polimilpa_token", data.access_token);
		setToken(data.access_token);

		const meRes = await fetchWithAuth("/v1/auth/me", {}, data.access_token);
		if (!meRes.ok) throw new Error("Failed to get user info");
		const me = (await meRes.json()) as User;
		setUser(me);
	}, []);

	const logout = useCallback(() => {
		localStorage.removeItem("polimilpa_token");
		setToken(null);
		setUser(null);
	}, []);

	return (
		<AuthContext.Provider value={{ user, token, loading, login, logout }}>
			{children}
		</AuthContext.Provider>
	);
}

export function useAuth() {
	const ctx = useContext(AuthContext);
	if (!ctx) throw new Error("useAuth must be used within AuthProvider");
	return ctx;
}
