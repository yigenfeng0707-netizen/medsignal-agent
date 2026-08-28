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
  useEffect,
  type ReactNode,
} from "react";
import { mockUsers, type UserInfo } from "./mock-data";
import { createUser, getUsers, type CreateUserRequest } from "./api";

interface UserContextValue {
  currentUser: UserInfo;
  userId: string; // "user_001" 形式，供 API 调用
  setUser: (user: UserInfo) => void;
  setUserId: (id: number) => void;
  users: UserInfo[];
  addUser: (input: CreateUserRequest) => Promise<UserInfo>;
  refreshUsers: () => Promise<void>;
}

const UserContext = createContext<UserContextValue | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  const [currentUser, setCurrentUser] = useState<UserInfo>(mockUsers[0]);
  const [users, setUsers] = useState<UserInfo[]>(mockUsers);

  const refreshUsers = useCallback(async () => {
    const remoteUsers = await getUsers();
    if (remoteUsers.length === 0) return;
    const normalized = remoteUsers.map((user) => ({
      ...user,
      conditions:
        mockUsers.find((item) => item.id === user.id)?.conditions ?? [],
    }));
    setUsers(normalized);
    setCurrentUser((selected) =>
      normalized.find((item) => item.id === selected.id) ?? normalized[0],
    );
  }, []);

  useEffect(() => {
    void refreshUsers();
  }, [refreshUsers]);

  const setUser = useCallback((user: UserInfo) => {
    setCurrentUser(user);
  }, []);

  const setUserId = useCallback((id: number) => {
    const u = users.find((x) => x.id === id);
    if (u) setCurrentUser(u);
  }, [users]);

  const addUser = useCallback(async (input: CreateUserRequest) => {
    const created = await createUser(input);
    if (!created) throw new Error("新增用户失败，请确认后端服务正常并检查填写内容");
    const normalized = { ...created, conditions: created.conditions ?? [] };
    setUsers((existing) => [...existing.filter((u) => u.id !== normalized.id), normalized]);
    setCurrentUser(normalized);
    return normalized;
  }, []);

  const userId = `user_${String(currentUser.id).padStart(3, "0")}`;

  return (
    <UserContext.Provider
      value={{ currentUser, userId, setUser, setUserId, users, addUser, refreshUsers }}
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
