/**
 * 状态管理 - AI 设计工作流 v2
 * 
 * 特性：
 * - 响应式状态
 * - 自动持久化
 * - 类型安全
 */

import { useState, useEffect, useCallback } from "react";

interface Project {
  project_name: string;
  brief: string;
  creation_time: number;
  status: string;
  current_step: string;
  tags: string[];
  market_analysis?: string;
  visual_research?: string;
  design_proposals?: string;
  images?: Array<{ image_path: string; prompt?: string }>;
}

interface UseProjectOptions {
  projectName: string | null;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface UseProjectReturn {
  project: Project | null;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
  updateProject: (data: Partial<Project>) => Promise<void>;
}

/**
 * 项目状态Hook
 */
export function useProject({
  projectName,
  autoRefresh = true,
  refreshInterval = 5000,
}: UseProjectOptions): UseProjectReturn {
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchProject = useCallback(async () => {
    if (!projectName) return;

    try {
      const response = await fetch(
        `/api/project/${encodeURIComponent(projectName)}`
      );
      
      if (!response.ok) {
        throw new Error(`获取项目失败: ${response.statusText}`);
      }

      const data = await response.json();
      setProject(data.data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    }
  }, [projectName]);

  const updateProject = useCallback(
    async (data: Partial<Project>) => {
      if (!projectName) return;

      try {
        const response = await fetch(
          `/api/project/${encodeURIComponent(projectName)}/update`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
          }
        );

        if (!response.ok) {
          throw new Error(`更新项目失败: ${response.statusText}`);
        }

        const updated = await response.json();
        setProject(updated.data);
      } catch (e) {
        throw e instanceof Error ? e : new Error(String(e));
      }
    },
    [projectName]
  );

  useEffect(() => {
    if (!projectName) {
      setProject(null);
      return;
    }

    setLoading(true);
    fetchProject().finally(() => setLoading(false));

    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(fetchProject, refreshInterval);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [projectName, autoRefresh, refreshInterval, fetchProject]);

  return {
    project,
    loading,
    error,
    refresh: fetchProject,
    updateProject,
  };
}

/**
 * 项目列表Hook
 */
export function useProjects(limit: number = 50) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchProjects = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/projects?limit=${limit}`);
      
      if (!response.ok) {
        throw new Error(`获取项目列表失败: ${response.statusText}`);
      }

      const data = await response.json();
      setProjects(data.data || []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  return {
    projects,
    loading,
    error,
    refresh: fetchProjects,
  };
}

/**
 * 工作流状态Hook
 */
interface WorkflowState {
  status: "idle" | "pending" | "in_progress" | "completed" | "failed";
  taskId: string | null;
  currentStep: string;
  progress: number;
  error: string | null;
}

export function useWorkflow(projectName: string | null) {
  const [workflowState, setWorkflowState] = useState<WorkflowState>({
    status: "idle",
    taskId: null,
    currentStep: "",
    progress: 0,
    error: null,
  });

  const startWorkflow = useCallback(
    async (brief: string, imageCount: number = 4) => {
      if (!projectName) return;

      try {
        const response = await fetch("/api/workflow/run_all", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_name: projectName,
            brief,
            image_count: imageCount,
          }),
        });

        if (!response.ok) {
          throw new Error("启动工作流失败");
        }

        const data = await response.json();
        setWorkflowState((prev) => ({
          ...prev,
          status: "pending",
          taskId: data.data.task_id,
        }));
      } catch (e) {
        setWorkflowState((prev) => ({
          ...prev,
          status: "failed",
          error: e instanceof Error ? e.message : String(e),
        }));
      }
    },
    [projectName]
  );

  const checkTaskStatus = useCallback(async () => {
    if (!workflowState.taskId) return;

    try {
      const response = await fetch(
        `/api/workflow/task/${workflowState.taskId}`
      );

      if (!response.ok) {
        throw new Error("检查任务状态失败");
      }

      const data = await response.json();
      const status = data.data.status;

      setWorkflowState((prev) => ({
        ...prev,
        status: status === "completed" ? "completed" : 
                status === "failed" ? "failed" : 
                status === "in_progress" ? "in_progress" : prev.status,
      }));
    } catch (e) {
      console.error("检查任务状态失败:", e);
    }
  }, [workflowState.taskId]);

  return {
    workflowState,
    setWorkflowState,
    startWorkflow,
    checkTaskStatus,
  };
}
