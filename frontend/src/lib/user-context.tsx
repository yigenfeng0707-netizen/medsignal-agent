"use client";

/**
 * 用户上下文：管理当前演示用户，全站共享。
 * 路演时一键切换张阿姨/李大爷/王先生，数据全站联动。
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { mockUsers, type UserInfo } from "./mock-data";

interface UserContextValue {
  currentUser: UserInfo;
  userId: string; // "user_001" 形式，供 API 调用
  setUser: (user: UserInfo) => void;
  setUserId: (id: number) => void;
  users: UserInfo[];
}

const UserContext = createContext<UserContextValue | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  const [currentUser, setCurrentUser] = useState<UserInfo>(mockUsers[0]);

  const setUser = useCallback((user: UserInfo) => {
    setCurrentUser(user);
  }, []);

  const setUserId = useCallback((id: number) => {
    const u = mockUsers.find((x) => x.id === id) || mockUsers[0];
    setCurrentUser(u);
  }, []);

  const userId = `user_${String(currentUser.id).padStart(3, "0")}`;

  return (
    <UserContext.Provider
      value={{ currentUser, userId, setUser, setUserId, users: mockUsers }}
    >
      {children}
    </UserContext.Provider>
  );
}

export function useUser(): UserContextValue {
  const ctx = useContext(UserContext);
  if (!ctx) {
    throw new Error("useUser 必须在 UserProvider 内使用");
  }
  return ctx;
}
