
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { 
  Loader2, RefreshCw, Download, Image as ImageIcon, FileText, 
  Sparkles, TrendingUp, Palette, CheckCircle2, CircleDashed,
  Wand2, 
  ChevronRight,
  Zap,
  LayoutGrid,
  ExternalLink,
  Share2,
  Settings,
  Plus,
  User,
  Key,
  Code,
  Copy
} from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import { cn } from "@/lib/utils"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

interface DashboardProps {
  project: string | null
  onProjectCreated: (projectName: string) => void
}

interface ProposalItem {
    image_path?: string;
    scheme?: string;
    concept?: string;
    inspiration?: string;
    description?: string;
    cmf?: string;
    prompt?: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [key: string]: any;
}

const STEPS = [
  { id: "market_analysis", label: "市场", icon: TrendingUp },
  { id: "visual_research", label: "视觉", icon: Palette },
  { id: "design_generation", label: "方案", icon: Sparkles },
  { id: "image_generation", label: "图库", icon: ImageIcon },
]

export function Dashboard({ project, onProjectCreated }: DashboardProps) {
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState("market_analysis")
  const [status, setStatus] = useState<string>("pending")
  const [currentStep, setCurrentStep] = useState<string>("")
  const [progress, setProgress] = useState(0)
  
  // Form State
  const [projectName, setProjectName] = useState("拍立得相机包")
  const [brief, setBrief] = useState("做一款拍立得相机包，需要参考市场中高端品牌的女性包包去结合设计一些相机包")
  const [modelName, setModelName] = useState("gemini-2.5-flash")
  
  // Data State
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [data, setData] = useState<Record<string, any>>({
    market_analysis: "",
    visual_research: "",
    design_proposals: "",
    full_report: "",
    images: []
  })

  // Use relative path to leverage Next.js Rewrites (proxy)
  // This avoids CORS and Mixed Content issues by making the request to the same origin (Vercel)
  // which then proxies to the backend defined in next.config.ts
  const API_URL = ""

  const [tags, setTags] = useState<string[]>([])
  const [isAutocompleteLoading, setIsAutocompleteLoading] = useState(false)
  const [isTagsLoading, setIsTagsLoading] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  
  // Settings State
  const [userPersona, setUserPersona] = useState("")
  const [jimengSessionId, setJimengSessionId] = useState("")
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [imageCount, setImageCount] = useState(4)
  const [appendCount, setAppendCount] = useState(4)
  const [isGeneratingMore, setIsGeneratingMore] = useState(false)
  
  // Ref for polling interval
  const pollIntervalRef = useState<{ current: NodeJS.Timeout | null }>({ current: null })[0]

  // Load settings from local storage
  useEffect(() => {
    const savedPersona = localStorage.getItem("userPersona")
    const savedSessionId = localStorage.getItem("jimengSessionId")
    if (savedPersona) setUserPersona(savedPersona)
    if (savedSessionId) setJimengSessionId(savedSessionId)
  }, [])

  // Save settings
  const saveSettings = () => {
      localStorage.setItem("userPersona", userPersona)
      localStorage.setItem("jimengSessionId", jimengSessionId)
      setSettingsOpen(false)
  }

  // Load Project Data
  useEffect(() => {
    let isMounted = true

    if (project) {
      setLoading(true)
      // Reset status to pending to show loading state immediately while fetching
      setStatus("pending") 
      
      fetch(`${API_URL}/api/project/${project}`)
        .then(res => res.json())
        .then(projectData => {
          if (!isMounted) return

          setProjectName(projectData.metadata.project_name)
          setBrief(projectData.metadata.brief)
          setStatus(projectData.metadata.status)
          setCurrentStep(projectData.metadata.current_step)
          setTags(projectData.metadata.tags || [])
          setData({
            market_analysis: projectData.market_analysis,
            visual_research: projectData.visual_research,
            design_proposals: projectData.design_proposals,
            full_report: projectData.full_report,
            images: projectData.images
          })
          
          if ((projectData.metadata.status === "in_progress" || projectData.metadata.status === "pending") && project === projectData.metadata.project_name) {
             // Clear any existing interval
             if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
             
             pollIntervalRef.current = setInterval(() => {
               fetch(`${API_URL}/api/project/${project}`)
                 .then(res => res.json())
                 .then(updatedData => {
                   if (!isMounted) return

                   setStatus(updatedData.metadata.status)
                   setCurrentStep(updatedData.metadata.current_step)
                   
                   // Auto-switch tab logic disabled as per user request
                   // if (updatedData.metadata.current_step && STEPS.some(s => s.id === updatedData.metadata.current_step)) {
                   //    setActiveTab(updatedData.metadata.current_step)
                   // }
                   
                   setData(prev => ({
                     ...prev,
                     market_analysis: updatedData.market_analysis,
                     visual_research: updatedData.visual_research,
                     design_proposals: updatedData.design_proposals,
                     full_report: updatedData.full_report,
                     images: updatedData.images
                   }))
                   
                   if (updatedData.metadata.status !== "in_progress" && updatedData.metadata.status !== "pending") {
                     if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
                   }
                 })
                 .catch(err => {
                   console.error("轮询失败:", err)
                   if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
                 })
             }, 2000)
           }
        })
        .catch(err => console.error(err))
        .finally(() => {
             if (isMounted) setLoading(false)
        })
    } else {
      setData({
        market_analysis: "",
        visual_research: "",
        design_proposals: "",
        full_report: "",
        images: []
      })
      setStatus("pending")
      setTags(["工业设计", "概念方案"])
    }

    return () => {
      isMounted = false
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
    }
  }, [project])

  const handleAutocomplete = async () => {
    if (!brief) return
    setIsAutocompleteLoading(true)
    // Clear brief to show streaming effect from start (optional, maybe better to append or replace)
    // setBrief("") 
    try {
      const res = await fetch(`${API_URL}/api/ai/autocomplete/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief, model_name: "models/gemma-3-12b-it" })
      })

      if (!res.body) throw new Error("No response body")
      
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let done = false
      let text = ""

      while (!done) {
        const { value, done: doneReading } = await reader.read()
        done = doneReading
        const chunkValue = decoder.decode(value, { stream: true })
        text += chunkValue
        setBrief(text)
      }
      
    } catch (e) {
      console.error("AI创意补全失败:", e)
      alert("AI创意补全失败，请检查网络连接")
    } finally {
      setIsAutocompleteLoading(false)
    }
  }

  const handleGenerateTags = async () => {
    if (!brief) return
    setIsTagsLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/ai/tags`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief, model_name: "gemini-2.5-flash" })
      })
      const data = await res.json()
      if (data.tags) {
        setTags(data.tags)
      }
    } catch (e) {
      console.error("推荐标签失败:", e)
      alert("推荐标签失败，请检查网络连接")
    } finally {
      setIsTagsLoading(false)
    }
  }

  const handleExport = async () => {
    if (!project) return
    setIsExporting(true)
    try {
      window.open(`${API_URL}/api/project/${project}/export`, "_blank")
    } catch (e) {
      console.error(e)
    } finally {
      setIsExporting(false)
    }
  }

  const handleShare = () => {
    const url = window.location.href
    navigator.clipboard.writeText(url)
    // Simple alert for now, could use a Toast component
    alert("链接已复制到剪贴板！") 
  }

  const handleGenerateMore = async () => {
    if (!project) return
    setIsGeneratingMore(true)
    try {
        const res = await fetch(`${API_URL}/api/workflow/generate-images`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                project_name: projectName,
                count: appendCount, 
                model_name: modelName,
                settings: {
                    persona: userPersona,
                    jimeng_session_id: jimengSessionId
                }
            })
        })
        const result = await res.json()
        if (result.status === "success") {
            // Reload project to get images
            const projRes = await fetch(`${API_URL}/api/project/${project}`)
            const projData = await projRes.json()
            setData(prev => ({ ...prev, images: projData.images }))
        }
    } catch (e) {
        console.error(e)
        alert("生成更多图片失败，请检查控制台日志")
    } finally {
        setIsGeneratingMore(false)
    }
  }

  const runStep = async (stepId: string) => {
    setLoading(true)
    setStatus("in_progress")
    setCurrentStep(stepId)
    try {
      // 检查是否可以使用流式接口（目前除了 image_generation 和 full_report 外都支持）
      const useStream = ["market_analysis", "visual_research", "design_generation"].includes(stepId)
      
      const endpoint = useStream ? `${API_URL}/api/workflow/step/stream` : `${API_URL}/api/workflow/step`
      
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_name: projectName,
          step: stepId,
          brief: brief,
          model_name: modelName,
          context: {
            market_analysis: data.market_analysis,
            visual_research: data.visual_research,
            design_proposals: data.design_proposals,
            design_prompts: data.design_proposals, // 修复：为image_generation步骤提供正确的键名
          },
          settings: {
            image_count: imageCount,
            persona: userPersona,
            jimeng_session_id: jimengSessionId
          }
        })
      })
      
      if (useStream) {
        if (!res.body) throw new Error("No response body")
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let done = false
        let text = ""
        
        while (!done) {
          const { value, done: doneReading } = await reader.read()
          done = doneReading
          const chunkValue = decoder.decode(value, { stream: true })
          text += chunkValue
          // 实时更新数据
          setData(prev => ({ ...prev, [stepId]: text }))
        }
        
        // 流式完成后，如果需要后续处理（比如通知创建项目），可以在这里做
        if (!project) {
            onProjectCreated(projectName)
        }
        
      } else {
        // 原有的非流式处理逻辑（用于 image_generation, full_report 等）
        const result = await res.json()
        if (result.status === "success") {
          if (stepId === "image_generation") {
            // Reload project to get images
            if (project) {
               const projRes = await fetch(`${API_URL}/api/project/${project}`)
               const projData = await projRes.json()
               setData(prev => ({ ...prev, images: projData.images }))
            }
          } else {
            setData(prev => ({ ...prev, [stepId]: result.result }))
          }
          
          if (!project) {
              onProjectCreated(projectName)
          }
        }
      }

    } catch (error) {
      console.error(error)
      setStatus("failed")
    } finally {
      setLoading(false)
      if (stepId === "full_report") setStatus("completed")
    }
  }

  const handleRunAll = async () => {
    setLoading(true)
    setStatus("in_progress")
    setProgress(5)
    
    try {
        // 调用新的异步全流程接口
        const res = await fetch(`${API_URL}/api/workflow/run_all`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                project_name: projectName,
                brief: brief,
                model_name: modelName,
                settings: {
                    image_count: imageCount,
                    persona: userPersona,
                    jimeng_session_id: jimengSessionId
                }
            })
        })
        
        if (res.ok) {
            console.log("全流程任务已提交后台运行")
            // 触发 onProjectCreated 以刷新侧边栏
            onProjectCreated(projectName)
            
            // 启动轮询 (useEffect 会自动处理 status="in_progress" 的轮询)
            // 这里我们只需要确保本地状态正确，让 useEffect 接管
        } else {
            throw new Error("Failed to start workflow")
        }
    } catch (e) {
        setStatus("failed")
        console.error("运行失败:", e)
        setLoading(false)
    }
    // 注意：这里不要 setLoading(false)，因为任务还在后台跑
    // setLoading(false) 会由轮询逻辑在检测到完成时触发
  }

  // --- Render Functions ---

  const renderTabContent = (rawContent: string) => {
    // 1. CRITICAL FIX: Clean content immediately to handle escaped newlines from backend
    // This ensures both JSON parsing and Markdown rendering get correct newline characters
    const content = rawContent ? rawContent.replace(/\\n/g, '\n') : "";

    if (!content) {
        return (
            <div className="py-24 text-center text-zinc-300">
                <FileText className="h-12 w-12 mx-auto mb-4 opacity-20" />
                <p>No content</p>
            </div>
        )
    }

    // Fix markdown formatting: add line breaks between common patterns
    const fixMarkdownFormat = (text: string): string => {
      if (!text) return ""
      let fixed = text
      
      // 1. Aggressively insert newlines before headers, BUT protect hex codes and tables
      // Exclude if preceded by | (table) or if it looks like a hex code #123
      // Using a simplified approach: Only insert if it looks like a block header
      fixed = fixed.replace(/([^|\n])\s*(#{1,6}\s)/g, '$1\n\n$2')
      
      // 2. Aggressively insert newlines before list items, BUT protect tables
      // Exclude if preceded by | (table separator or cell)
      fixed = fixed.replace(/([^|\n])\s*([*-]\s)/g, '$1\n\n$2')
      fixed = fixed.replace(/([^|\n])\s*(\d+\.\s)/g, '$1\n\n$2')

      // 3. Ensure headers have enough spacing even if they have one newline
      fixed = fixed.replace(/\n(#{1,6}\s)/g, '\n\n$1')

      // 4. Clean up excessive newlines
      fixed = fixed.replace(/\n{3,}/g, '\n\n')
      
      return fixed
    }

    const processedContent = fixMarkdownFormat(content)

    // Try to parse as JSON
    let parsedData = null
    let isJson = false

    const trimmedContent = processedContent.trim()
    
    // Check if content is markdown (starts with #, >, or contains |)
    const isMarkdownContent = trimmedContent.startsWith('#') || 
                              trimmedContent.startsWith('>') || 
                              trimmedContent.includes('|') ||
                              trimmedContent.includes('```') ||
                              trimmedContent.includes('---')

    // Only try JSON parsing if it doesn't look like markdown and starts with { or [
    if (!isMarkdownContent && (trimmedContent.startsWith('{') || trimmedContent.startsWith('['))) {
      // 1. Try direct parse
      try {
        parsedData = JSON.parse(trimmedContent)
      } catch (e) {
        // Failed direct parse
      }

      // 2. If failed, try extracting from markdown code block
      if (!parsedData) {
        const jsonMatch = processedContent.match(/```json\s*(\{[\s\S]*?\})\s*```/)
        if (jsonMatch && jsonMatch[1]) {
          try {
            parsedData = JSON.parse(jsonMatch[1])
          } catch (e) {
            // Failed markdown parse
          }
        }
      }

      // 3. If still failed, try finding first '{' and last '}'
      if (!parsedData) {
        const firstOpen = processedContent.indexOf('{')
        const lastClose = processedContent.lastIndexOf('}')
        if (firstOpen !== -1 && lastClose !== -1 && lastClose > firstOpen) {
          try {
            const potentialJson = processedContent.substring(firstOpen, lastClose + 1)
            parsedData = JSON.parse(potentialJson)
          } catch (e) {
            // Failed substring parse
          }
        }
      }
    }

    if (parsedData) {
      isJson = true
    }

    const MarkdownRenderer = ({ children }: { children: string }) => (
        <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
                h1: ({ node, ...props }) => <h1 {...props} className="text-zinc-900 dark:text-white" />,
                h2: ({ node, ...props }) => (
                    <h2 {...props} className="text-zinc-800 dark:text-zinc-100 group">
                        <span className="w-1.5 h-6 bg-zinc-900 dark:bg-zinc-100 rounded-full inline-block mr-2 align-middle" />
                        <span className="align-middle">{props.children}</span>
                    </h2>
                ),
                h3: ({ node, ...props }) => <h3 {...props} className="text-zinc-800 dark:text-zinc-200 mt-8 mb-4 font-bold" />,
                img: ({ node, ...props }) => {
                    const src = typeof props.src === 'string' ? props.src : '';
                    const isRelative = src && !src.startsWith('http') && !src.startsWith('https') && !src.startsWith('/');
                    // If src is relative path like "image.jpg", prepend project path
                    // If API_URL is empty (proxy mode), the final path will be /projects/... which Next.js rewrites handle
                    const finalSrc = isRelative ? `/projects/${project}/${src}` : src;
                    return (
                        <span className="block my-10 flex flex-col items-center gap-3">
                            <img 
                                {...props} 
                                src={finalSrc} 
                                className="max-w-full max-h-[500px] object-contain rounded-2xl shadow-2xl border border-zinc-200 dark:border-zinc-800 transition-transform hover:scale-[1.01]" 
                            />
                            {props.alt && <span className="text-xs font-medium text-zinc-400 italic">图示：{props.alt}</span>}
                        </span>
                    );
                },
                table: ({ node, ...props }) => (
                    <div className="my-8 overflow-hidden border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm">
                        <table {...props} className="min-w-full divide-y divide-zinc-200 dark:divide-zinc-800" />
                    </div>
                ),
                blockquote: ({ node, ...props }) => (
                    <blockquote {...props} className="not-prose my-8 border-l-4 border-zinc-900 dark:border-zinc-100 bg-zinc-50 dark:bg-zinc-800/50 p-6 rounded-r-2xl text-zinc-700 dark:text-zinc-300 italic shadow-sm" />
                )
            }}
        >
            {children}
        </ReactMarkdown>
    )

    if (isJson && parsedData) {
        // Special rendering for Design Generation (Design Proposals), Market Analysis, and Visual Research
        if (["design_generation", "market_analysis", "visual_research"].includes(activeTab)) {
            const coreIdea = parsedData.summary || parsedData.core_idea || "";
            const prompts = parsedData.prompts || parsedData.visuals || [];
            
            // Fallback: If no prompts, render raw content
            if (!prompts || prompts.length === 0) {
                 return (
                    <div className="prose prose-zinc prose-lg max-w-none dark:prose-invert">
                        <MarkdownRenderer>{processedContent}</MarkdownRenderer>
                    </div>
                )
            }

            return (
                <div className="space-y-12 animate-in fade-in duration-500">
                    {/* Core Idea Section */}
                    {coreIdea && (
                        <div className="bg-gradient-to-br from-zinc-900 to-zinc-800 dark:from-zinc-800 dark:to-zinc-950 p-8 rounded-3xl shadow-xl text-white relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full blur-3xl -mr-32 -mt-32"></div>
                            <div className="relative z-10">
                                <h4 className="flex items-center gap-3 text-white/60 font-bold mb-4 text-xs uppercase tracking-widest">
                                    <Sparkles className="h-4 w-4" /> 提案核心策略
                                </h4>
                                <p className="text-base md:text-lg font-medium leading-relaxed opacity-90">
                                    {coreIdea}
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Proposals Grid */}
                    <div className="grid gap-12">
                        {prompts.map((item: ProposalItem, i: number) => (
                            <div key={i} className="group relative bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 overflow-hidden shadow-sm hover:shadow-xl transition-all duration-500">
                                <div className="grid md:grid-cols-2 gap-0 h-full">
                                    {/* Left: Image */}
                                    <div className="relative h-[400px] md:h-auto bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
                                        {item.image_path ? (
                                            <img 
                                                src={`${API_URL}${item.image_path}`} 
                                                alt={item.scheme || item.concept || `Proposal ${i+1}`}
                                                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                                            />
                                        ) : (
                                            <div className="w-full h-full flex flex-col items-center justify-center text-zinc-400">
                                                <ImageIcon className="h-12 w-12 mb-4 opacity-20" />
                                                <p className="text-xs uppercase tracking-widest">等待绘图生成...</p>
                                            </div>
                                        )}
                                        <div className="absolute top-4 left-4 bg-white/90 dark:bg-zinc-900/90 backdrop-blur px-3 py-1 rounded-full text-xs font-bold shadow-sm">
                                            方案 0{i + 1}
                                        </div>
                                    </div>

                                    {/* Right: Content */}
                                    <div className="p-8 md:p-10 flex flex-col h-full">
                                        <div className="mb-6">
                                            <h3 className="text-2xl font-display font-bold text-zinc-900 dark:text-white mb-2">
                                                {item.scheme || item.concept || `方案 ${i+1}`}
                                            </h3>
                                            <div className="h-1 w-12 bg-zinc-900 dark:bg-white rounded-full"></div>
                                        </div>

                                        <div className="space-y-6 flex-1">
                                            {item.inspiration && (
                                                <div>
                                                    <h5 className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 mb-2 flex items-center gap-2">
                                                        <Zap className="h-3 w-3" /> 创意源泉
                                                    </h5>
                                                    <p className="text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed">
                                                        {item.inspiration}
                                                    </p>
                                                </div>
                                            )}
                                            
                                            {item.description && (
                                                <div>
                                                    <h5 className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 mb-2 flex items-center gap-2">
                                                        <FileText className="h-3 w-3" /> 设计故事
                                                    </h5>
                                                    <p className="text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed">
                                                        {item.description}
                                                    </p>
                                                </div>
                                            )}

                                            {item.cmf && (
                                                <div>
                                                    <h5 className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 mb-2 flex items-center gap-2">
                                                        <Palette className="h-3 w-3" /> CMF 定义
                                                    </h5>
                                                    <p className="text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed">
                                                        {item.cmf}
                                                    </p>
                                                </div>
                                            )}
                                        </div>

                                        {item.prompt && (
                                            <div className="mt-8 pt-6 border-t border-zinc-100 dark:border-zinc-800">
                                                <div className="flex items-center justify-between mb-3">
                                                    <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-2">
                                                        <Code className="h-3 w-3" /> 绘图 Prompt
                                                    </span>
                                                    <Button 
                                                        variant="ghost" 
                                                        size="sm" 
                                                        className="h-6 text-[10px] hover:bg-zinc-100 dark:hover:bg-zinc-800"
                                                        onClick={() => {
                                                            if (item.prompt) {
                                                                navigator.clipboard.writeText(item.prompt);
                                                                alert("提示词已复制！");
                                                            }
                                                        }}
                                                    >
                                                        <Copy className="h-3 w-3 mr-1" /> 复制
                                                    </Button>
                                                </div>
                                                <div className="bg-zinc-50 dark:bg-zinc-950 p-3 rounded-lg border border-zinc-100 dark:border-zinc-800">
                                                    <p className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400 leading-relaxed line-clamp-3 hover:line-clamp-none transition-all cursor-text select-text">
                                                        {item.prompt}
                                                    </p>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            );
        }

        return (
            <div className="space-y-8 animate-in fade-in duration-500">
                {/* Summary Section */}
                {parsedData.summary && (
                    <div className="bg-emerald-50 dark:bg-emerald-950/30 p-6 rounded-2xl border border-emerald-100 dark:border-emerald-900/50 shadow-sm">
                        <h4 className="flex items-center gap-2 text-emerald-800 dark:text-emerald-400 font-bold mb-3 text-sm uppercase tracking-wider">
                            <Sparkles className="h-4 w-4" /> 核心摘要
                        </h4>
                        <p className="text-emerald-900 dark:text-emerald-100 text-base leading-relaxed font-medium">
                            {parsedData.summary}
                        </p>
                    </div>
                )}
                
                {/* Main Content */}
                {parsedData.content && (
                    <div className="prose prose-zinc prose-lg max-w-none dark:prose-invert 
                        prose-headings:font-display prose-headings:font-bold prose-headings:tracking-tight 
                        prose-h1:text-4xl prose-h1:mb-8 prose-h1:pb-4 prose-h1:border-b prose-h1:border-zinc-100 dark:prose-h1:border-zinc-800
                        prose-h2:text-2xl prose-h2:mt-12 prose-h2:mb-6 prose-h2:flex prose-h2:items-center
                        prose-p:text-zinc-600 dark:prose-p:text-zinc-400 prose-p:leading-relaxed prose-p:mb-6
                        prose-li:text-zinc-600 dark:prose-li:text-zinc-400 prose-li:mb-2
                        prose-strong:text-zinc-900 dark:prose-strong:text-white
                        prose-th:bg-zinc-50 dark:prose-th:bg-zinc-800 prose-th:px-4 prose-th:py-3 prose-th:text-xs prose-th:font-bold prose-th:uppercase prose-th:tracking-wider
                        prose-td:px-4 prose-td:py-3 prose-td:text-sm prose-td:border-t prose-td:border-zinc-100 dark:prose-td:border-zinc-800">
                        <MarkdownRenderer>{fixMarkdownFormat(parsedData.content.replace(/\\n/g, '\n'))}</MarkdownRenderer>
                    </div>
                )}
                
                {/* Prompts/Visuals Section */}
                {(parsedData.visuals || parsedData.prompts) && (
                    <div className="space-y-6 pt-8 border-t border-zinc-200 dark:border-zinc-800">
                        <h3 className="text-xl font-display font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                             <ImageIcon className="h-5 w-5 text-zinc-500" /> 
                             视觉方案与提示词
                        </h3>
                        <div className="grid gap-4 md:grid-cols-2">
                            {(parsedData.visuals || parsedData.prompts).map((item: ProposalItem, i: number) => (
                                <div key={i} className="bg-zinc-50 dark:bg-zinc-900/50 p-5 rounded-xl border border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors group">
                                    <div className="flex items-center gap-2 mb-3">
                                        <span className="flex items-center justify-center w-6 h-6 rounded-full bg-zinc-200 dark:bg-zinc-800 text-xs font-bold text-zinc-600 dark:text-zinc-400">
                                            {i + 1}
                                        </span>
                                        <span className="font-bold text-zinc-900 dark:text-zinc-100 text-sm">
                                            {item.concept || item.scheme || `方案 ${i+1}`}
                                        </span>
                                    </div>
                                    
                                    {/* Image Display if available */}
                                    {item.image_path && (
                                        <div className="mb-4 aspect-square overflow-hidden rounded-lg bg-white dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-800">
                                            <img 
                                                src={`${API_URL}${item.image_path}`} 
                                                alt={item.concept || "Generated Image"}
                                                className="w-full h-full object-cover hover:scale-105 transition-transform duration-500"
                                            />
                                        </div>
                                    )}

                                    <div className="bg-white dark:bg-zinc-950 p-3 rounded-lg border border-zinc-100 dark:border-zinc-800 shadow-inner">
                                        <p className="text-zinc-500 dark:text-zinc-400 font-mono text-[10px] leading-relaxed line-clamp-4 group-hover:line-clamp-none transition-all">
                                            {item.prompt}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        )
    }

    // UI Optimization: Transform standard Markdown into Cards for Market/Visual tabs
    // This allows them to look like the "Solution" tab even without JSON structure
    if (["market_analysis", "visual_research"].includes(activeTab)) {
        // 1. Determine separator (H2 or H3) based on content availability
        // Priority: H2 (##) -> H3 (###)
        const hasH2 = /^##\s/m.test(processedContent);
        const splitRegex = hasH2 ? /(?=^##\s)/m : /(?=^###\s)/m;
        
        // 2. Split content into sections
        const sections = processedContent.split(splitRegex);
        
        // 3. Filter out empty sections
        const nonEmptySections = sections.filter(s => s.trim().length > 0);
        
        if (nonEmptySections.length > 0) {
            // The first section might be intro (if it doesn't start with the separator)
            let intro = "";
            let rawCards = nonEmptySections;
            
            // Check if the first section is actually a header section
            const firstSectionRaw = nonEmptySections[0].trim();
            const headerPrefix = hasH2 ? "## " : "### ";
            
            if (!firstSectionRaw.startsWith(headerPrefix)) {
                intro = nonEmptySections[0];
                rawCards = nonEmptySections.slice(1);
            }

            // 4. Parse and Clean Cards Data
            const cardsData = rawCards.map(section => {
                const lines = section.trim().split('\n');
                const titleLine = lines[0];
                const contentBody = lines.slice(1).join('\n').trim();
                
                // Clean title: remove hashes, bold markers, colons
                const title = titleLine
                    .replace(/^(#{2,3})\s+/, '') // Remove ## or ###
                    .replace(/\*\*/g, '')        // Remove **
                    .replace(/[:：]/g, '')        // Remove colons
                    .trim();

                return { title, content: contentBody };
            }).filter(card => card.content.length > 0); // Ensure content is not empty

            if (cardsData.length > 0) {
                return (
                    <div className="space-y-12 animate-in fade-in duration-500">
                        {/* Intro/Core Idea Section */}
                        {intro && (
                            <div className="text-white relative overflow-hidden">
                                 <div className="relative z-10">
                                     <h4 className="flex items-center gap-3 font-bold mb-4 text-xs uppercase tracking-widest text-white/60">
                                         <Sparkles className="h-4 w-4" /> 
                                         {activeTab === "market_analysis" ? "市场洞察摘要" : "视觉研究摘要"}
                                     </h4>
                                     <div className="text-base md:text-lg font-medium leading-relaxed opacity-90 prose prose-invert max-w-none">
                                         <MarkdownRenderer>{intro}</MarkdownRenderer>
                                     </div>
                                 </div>
                            </div>
                        )}

                        {/* Content Cards Grid */}
                        <div className="grid gap-8 md:grid-cols-1"> 
                            {cardsData.map((card, i) => (
                                <div key={i} className="bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 overflow-hidden shadow-sm hover:shadow-xl transition-all duration-500 flex flex-col">
                                    <div className="p-8 md:p-10 flex-1">
                                        <h3 className="text-2xl font-display font-bold text-zinc-900 dark:text-white mb-6 flex items-center gap-3">
                                            <span className="flex items-center justify-center w-8 h-8 rounded-full bg-zinc-100 dark:bg-zinc-800 text-sm font-bold text-zinc-500">
                                                {i + 1}
                                            </span>
                                            {card.title}
                                        </h3>
                                        <div className="prose prose-zinc prose-lg max-w-none dark:prose-invert">
                                             <MarkdownRenderer>{card.content}</MarkdownRenderer>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                );
            }
        }
    }

    // Default Markdown Rendering (for non-JSON content)
    return (
        <div className="prose prose-zinc prose-lg max-w-none dark:prose-invert 
            prose-headings:font-display prose-headings:font-bold prose-headings:tracking-tight 
            prose-h1:text-4xl prose-h1:mb-8 prose-h1:pb-4 prose-h1:border-b prose-h1:border-zinc-100 dark:prose-h1:border-zinc-800
            prose-h2:text-2xl prose-h2:mt-12 prose-h2:mb-6 prose-h2:flex prose-h2:items-center
            prose-p:text-zinc-600 dark:prose-p:text-zinc-400 prose-p:leading-relaxed prose-p:mb-6
            prose-li:text-zinc-600 dark:prose-li:text-zinc-400 prose-li:mb-2
            prose-strong:text-zinc-900 dark:prose-strong:text-white
            prose-th:bg-zinc-50 dark:prose-th:bg-zinc-800 prose-th:px-4 prose-th:py-3 prose-th:text-xs prose-th:font-bold prose-th:uppercase prose-th:tracking-wider
            prose-td:px-4 prose-td:py-3 prose-td:text-sm prose-td:border-t prose-td:border-zinc-100 dark:prose-td:border-zinc-800">
            <MarkdownRenderer>{processedContent}</MarkdownRenderer>
        </div>
    )
  }

  const renderHome = () => (
    <div className="flex-1 flex flex-col items-center justify-start p-6 overflow-y-auto custom-scrollbar bg-zinc-50/50 dark:bg-zinc-950 relative">
        {/* Settings Button */}
        <div className="absolute top-6 right-6">
            <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
                <DialogTrigger asChild>
                    <Button variant="ghost" size="icon" className="hover:bg-zinc-200 dark:hover:bg-zinc-800 rounded-full">
                        <Settings className="h-5 w-5 text-zinc-500" />
                    </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[425px] bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
                    <DialogHeader>
                        <DialogTitle className="text-zinc-900 dark:text-white">系统设置</DialogTitle>
                        <DialogDescription className="text-zinc-500">
                            配置您的 AI 工作流偏好与 API 设置。
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="persona" className="text-zinc-900 dark:text-white flex items-center gap-2">
                                <User className="h-4 w-4" /> 个性化角色 (Persona)
                            </Label>
                            <Input
                                id="persona"
                                value={userPersona}
                                onChange={(e) => setUserPersona(e.target.value)}
                                placeholder="例如：资深工业设计师 / 材质专家"
                                className="col-span-3 bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800"
                            />
                            <p className="text-[10px] text-zinc-400">
                                设定 AI 的思考视角，如“注重材质的建模师”或“注重光影的摄影师”。
                            </p>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="session-id" className="text-zinc-900 dark:text-white flex items-center gap-2">
                                <Key className="h-4 w-4" /> 即梦 SessionID
                            </Label>
                            <Input
                                id="session-id"
                                value={jimengSessionId}
                                onChange={(e) => setJimengSessionId(e.target.value)}
                                placeholder="输入您的 Jimeng SessionID 以提升额度"
                                className="col-span-3 bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800"
                                type="password"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button onClick={saveSettings} className="bg-zinc-900 text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900">保存设置</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>

        <section className="w-full max-w-4xl space-y-8 my-auto py-8">
            <div className="text-center space-y-2">
                <h3 className="text-3xl font-display font-bold text-zinc-900 dark:text-white tracking-tight">
                    开启新创作
                </h3>
                <p className="text-zinc-500 dark:text-zinc-400 text-base">
                    在下方定义您的项目详情，生成工业设计创意方案。
                </p>
            </div>

            <div className="space-y-4">
                <div className="bg-white dark:bg-zinc-900 p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 shadow-sm hover:shadow-md transition-all">
                    <div className="flex flex-col space-y-1">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 px-1">
                            项目名称
                        </label>
                        <input 
                            value={projectName}
                            onChange={(e) => setProjectName(e.target.value)}
                            className="w-full text-xl font-display font-semibold border-none focus:ring-0 p-1 placeholder-zinc-300 bg-transparent dark:text-white" 
                            placeholder="例如：简约咖啡机概念设计" 
                            type="text"
                        />
                    </div>
                </div>

                <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 shadow-sm overflow-hidden hover:shadow-md transition-all">
                    <div className="p-6 pb-2">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-400">
                            设计需求描述
                        </label>
                    </div>
                    <div className="px-6 pb-6 space-y-4">
                        <textarea 
                            value={brief}
                            onChange={(e) => setBrief(e.target.value)}
                            className="w-full text-lg border-none focus:ring-0 p-0 resize-none placeholder-zinc-300 text-zinc-700 dark:text-zinc-300 bg-transparent leading-relaxed" 
                            placeholder="描述产品目标、目标受众和审美趋势..." 
                            rows={4}
                        />
                        <div className="flex items-center justify-between pt-4 border-t border-zinc-50 dark:border-zinc-800">
                            <Button 
                                variant="ghost" 
                                className="text-zinc-900 font-bold gap-2 hover:bg-zinc-100 dark:text-zinc-100 dark:hover:bg-zinc-800 py-1 h-8 text-xs"
                                onClick={handleAutocomplete}
                                disabled={isAutocompleteLoading}
                            >
                                {isAutocompleteLoading ? (
                                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                ) : (
                                    <Sparkles className="h-3.5 w-3.5" />
                                )}
                                AI 创意补全
                            </Button>
                            <div className="flex gap-2 items-center">
                                {tags.map((tag, i) => (
                                    <span key={i} className="px-2.5 py-0.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-500 rounded-full text-[9px] font-bold uppercase tracking-tight">
                                        {tag}
                                    </span>
                                ))}
                                <Button 
                                    variant="ghost" 
                                    size="icon" 
                                    className="h-5 w-5 rounded-full" 
                                    onClick={handleGenerateTags}
                                    disabled={isTagsLoading}
                                >
                                    {isTagsLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="bg-white dark:bg-zinc-900 p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 shadow-sm hover:shadow-md transition-all">
                     <div className="flex items-center justify-between mb-4">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 px-1">
                            生成图片数量: {imageCount}
                        </label>
                     </div>
                     <input 
                        type="range" 
                        min="1" 
                        max="8" 
                        step="1" 
                        value={imageCount}
                        onChange={(e) => setImageCount(parseInt(e.target.value))}
                        className="w-full h-2 bg-zinc-200 rounded-lg appearance-none cursor-pointer dark:bg-zinc-700 accent-zinc-900 dark:accent-zinc-100"
                     />
                     <div className="flex justify-between text-xs text-zinc-400 mt-2 font-mono">
                        <span>1</span>
                        <span>4 (默认)</span>
                        <span>8</span>
                     </div>
                </div>

                <div className="flex justify-center pt-4">
                    <Button 
                        onClick={handleRunAll}
                        disabled={loading}
                        className="h-14 px-12 text-lg font-display font-bold bg-zinc-900 text-white rounded-xl hover:scale-[1.02] active:scale-95 transition-all shadow-xl shadow-zinc-200 dark:bg-zinc-100 dark:text-zinc-900 dark:shadow-none"
                    >
                        <Zap className="mr-2 h-5 w-5 fill-current" />
                        运行全流程 (点击开始)
                    </Button>
                </div>
            </div>
        </section>
    </div>
  )

  const renderLoading = () => (
    <div className="flex-1 flex flex-col items-center justify-start p-6 overflow-y-auto custom-scrollbar bg-zinc-50/50 dark:bg-zinc-950">
        <div className="max-w-md w-full text-center space-y-8 my-auto py-8">
            <div className="relative flex items-center justify-center">
                <div className="w-24 h-24 rounded-full border-4 border-zinc-100 dark:border-zinc-800"></div>
                <div className="absolute w-24 h-24 rounded-full border-4 border-t-zinc-900 border-r-transparent border-b-transparent border-l-transparent animate-spin dark:border-t-zinc-100"></div>
                <div className="absolute flex flex-col items-center">
                    <span className="text-2xl font-display font-bold text-zinc-900 dark:text-white">{progress}%</span>
                </div>
            </div>

            <div className="space-y-2">
                <h2 className="text-xl font-display font-bold text-zinc-900 dark:text-white tracking-tight">
                    正在生成设计方案...
                </h2>
                <p className="text-xs text-zinc-500">
                    当前项目: {projectName}
                </p>
            </div>

            <div className="space-y-4">
                <div className="w-full bg-zinc-200 dark:bg-zinc-800 h-1 rounded-full overflow-hidden">
                    <div 
                        className="bg-zinc-900 h-full rounded-full transition-all duration-500 dark:bg-zinc-100" 
                        style={{ width: `${progress}%` }}
                    />
                </div>
                
                <div className="grid grid-cols-2 gap-y-3 gap-x-6">
                    {STEPS.map((s, i) => {
                        const isDone = progress > (i + 1) * 20 || status === "completed"
                        const isCurrent = currentStep === s.id
                        return (
                            <div key={s.id} className={cn(
                                "flex items-center gap-2 text-[10px] font-medium transition-colors",
                                isDone ? "text-emerald-600" : isCurrent ? "text-zinc-900 dark:text-white" : "text-zinc-400"
                            )}>
                                {isDone ? (
                                    <CheckCircle2 className="h-3.5 w-3.5" />
                                ) : isCurrent ? (
                                    <CircleDashed className="h-3.5 w-3.5 animate-spin" />
                                ) : (
                                    <div className="w-3.5 h-3.5 rounded-full border-2 border-current opacity-20" />
                                )}
                                <span>{s.label}</span>
                            </div>
                        )
                    })}
                </div>
            </div>
        </div>
    </div>
  )

  const renderResults = () => (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-zinc-50/50 dark:bg-zinc-950">
        {/* Sticky Header */}
        <header className="bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 px-8 py-4 flex-shrink-0">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    <CheckCircle2 className={cn("h-5 w-5", status === "completed" ? "text-emerald-500" : "text-zinc-400")} />
                    <h2 className="text-xl font-display font-bold text-zinc-900 dark:text-white">
                        成果展示: {projectName}
                    </h2>
                    {status === "in_progress" && (
                        <div className="flex items-center gap-2 px-3 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-full text-xs font-bold animate-pulse">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            <span>AI 正在思考: {STEPS.find(s => s.id === currentStep)?.label || "处理中"}...</span>
                        </div>
                    )}
                </div>
                <div className="flex items-center gap-3">
                    {status === "completed" && (
                        <div className="flex items-center gap-2 text-sm text-emerald-600 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-100 dark:border-emerald-900 px-3 py-1.5 rounded-full font-medium">
                            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                            <span>生成完毕</span>
                        </div>
                    )}
                </div>
            </div>

            <div className="bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-xl overflow-hidden flex divide-x divide-zinc-200 dark:divide-zinc-700">
                <div className="p-4 flex-1">
                    <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 mb-1 block">项目摘要</label>
                    <h3 className="text-base font-display font-bold text-zinc-900 dark:text-white">{projectName}</h3>
                    <div className="flex gap-2 mt-2">
                        <span className="px-2 py-0.5 bg-zinc-200 dark:bg-zinc-700 text-zinc-500 rounded text-[9px] font-bold uppercase tracking-tight">#工业设计</span>
                        <span className="px-2 py-0.5 bg-zinc-200 dark:bg-zinc-700 text-zinc-500 rounded text-[9px] font-bold uppercase tracking-tight">#概念方案</span>
                    </div>
                </div>
                <div className="p-4 flex-[2]">
                    <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 mb-1 block">设计需求</label>
                    <p className="text-zinc-600 dark:text-zinc-400 text-xs leading-relaxed line-clamp-2 italic">
                        &quot;{brief}&quot;
                    </p>
                </div>
            </div>
        </header>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
            <div className="max-w-[1400px] mx-auto p-8 space-y-8">
                <div className="flex items-center justify-between gap-4 border-b border-zinc-200 dark:border-zinc-800 pb-4">
                    <div className="flex bg-zinc-100 dark:bg-zinc-800 p-1 rounded-lg">
                        {STEPS.map(step => {
                            // Check status
                            let isCompleted = false;
                            if (step.id === "market_analysis") isCompleted = !!data.market_analysis;
                            else if (step.id === "visual_research") isCompleted = !!data.visual_research;
                            else if (step.id === "design_generation") isCompleted = !!data.design_proposals;
                            else if (step.id === "image_generation") isCompleted = data.images && data.images.length > 0;

                            return (
                                <button
                                    key={step.id}
                                    onClick={() => setActiveTab(step.id)}
                                    className={cn(
                                        "px-4 py-2 text-xs font-bold rounded-md flex items-center gap-2 transition-all relative",
                                        activeTab === step.id 
                                            ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-white" 
                                            : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-300"
                                    )}
                                >
                                    <step.icon className="h-4 w-4" />
                                    {step.label}
                                    <span className={cn(
                                        "w-1.5 h-1.5 rounded-full ml-1",
                                        isCompleted ? "bg-emerald-500" : "bg-zinc-300 dark:bg-zinc-600"
                                    )} />
                                </button>
                            )
                        })}
                    </div>
                    <div className="flex gap-3">
                        <Button 
                            className="bg-zinc-900 text-white hover:bg-zinc-800 gap-2 font-bold text-sm dark:bg-zinc-100 dark:text-zinc-900"
                            onClick={handleExport}
                            disabled={isExporting}
                        >
                            {isExporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                            全部导出
                        </Button>
                        <Button 
                            variant="outline" 
                            size="icon" 
                            className="border-zinc-200 dark:border-zinc-800"
                            onClick={handleShare}
                        >
                            <Share2 className="h-4 w-4 text-zinc-500" />
                        </Button>
                    </div>
                </div>

                <div className="mt-8">
                    {activeTab === "image_generation" ? (
                        <div className="space-y-6">
                             <div className="flex justify-between items-center">
                                 <div className="space-y-1">
                                     <h3 className="text-lg font-display font-bold text-zinc-900 dark:text-white">创意方案图库</h3>
                                     <p className="text-xs text-zinc-500">基于当前设计提案生成的视觉方案。</p>
                                 </div>
                                 <div className="flex items-center gap-2">
                                     <select 
                                         className="h-9 rounded-md border border-zinc-200 bg-white px-3 py-1 text-xs font-medium shadow-sm focus:outline-none dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-100"
                                         value={appendCount}
                                         onChange={(e) => setAppendCount(parseInt(e.target.value))}
                                     >
                                         <option value={2}>+2张</option>
                                         <option value={4}>+4张</option>
                                         <option value={8}>+8张</option>
                                         <option value={12}>+12张</option>
                                         <option value={20}>+20张</option>
                                     </select>
                                     <Button 
                                         onClick={handleGenerateMore} 
                                         disabled={isGeneratingMore}
                                         className="bg-zinc-900 text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 text-xs h-9 px-4"
                                     >
                                         {isGeneratingMore ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-2" /> : <Plus className="h-3.5 w-3.5 mr-2" />}
                                         追加生成
                                     </Button>
                                 </div>
                             </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {(() => {
                                    // Try to merge images with prompts from design_proposals
                                    let galleryItems = [];
                                    
                                    // 1. Try to parse design_proposals to get structured prompts
                                    const promptsMap = new Map();
                                    try {
                                        if (data.design_proposals && data.design_proposals.trim().startsWith('{')) {
                                            const parsed = JSON.parse(data.design_proposals);
                                            if (parsed.prompts && Array.isArray(parsed.prompts)) {
                                                parsed.prompts.forEach((p: ProposalItem) => {
                                                    if (p.image_path) {
                                                        // Normalize path to match data.images format
                                                        const normalizedPath = p.image_path.startsWith('/') ? p.image_path : `/${p.image_path}`;
                                                        promptsMap.set(normalizedPath, p.prompt);
                                                    }
                                                });
                                            }
                                        }
                                    } catch (e) {
                                        console.error("Failed to parse design proposals for gallery", e);
                                    }

                                    // 2. Map data.images to items
                                    if (data.images && data.images.length > 0) {
                                        galleryItems = data.images.map((img: string) => ({
                                            src: img,
                                            prompt: promptsMap.get(img) || ""
                                        }));
                                    }
                                    
                                    return galleryItems.length > 0 ? (
                                        galleryItems.map((item: ProposalItem & { src: string }, idx: number) => (
                                            <div key={idx} className="group relative bg-white dark:bg-zinc-900 rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-800 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 flex flex-col">
                                                <div className="aspect-[4/5] overflow-hidden bg-zinc-100 dark:bg-zinc-800 relative">
                                                    <img 
                                                        src={`${API_URL}${item.src}`} 
                                                        alt={`Concept ${idx + 1}`}
                                                        className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                                                    />
                                                    <div className="absolute inset-0 bg-gradient-to-t from-zinc-900/90 via-zinc-900/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-6">
                                                        <div className="translate-y-4 group-hover:translate-y-0 transition-transform duration-300">
                                                            <div className="flex gap-2 mt-4">
                                                                <Button variant="secondary" size="sm" className="flex-1 font-bold text-[10px] uppercase tracking-wider" asChild>
                                                                    <a href={`${API_URL}${item.src}`} download target="_blank">立即下载</a>
                                                                </Button>
                                                                <Button variant="secondary" size="icon" className="bg-white/20 backdrop-blur-md text-white border-none hover:bg-white/40">
                                                                    <ExternalLink className="h-4 w-4" />
                                                                </Button>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                                
                                                {/* Prompt Display Section */}
                                                {item.prompt && (
                                                    <div className="p-4 border-t border-zinc-100 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 flex-1 flex flex-col">
                                                        <div className="flex items-center justify-between mb-2">
                                                            <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">Prompt</span>
                                                            <Button 
                                                                variant="ghost" 
                                                                size="sm" 
                                                                className="h-6 text-[10px] hover:bg-zinc-200 dark:hover:bg-zinc-800"
                                                                onClick={() => {
                                                                    if (item.prompt) {
                                                                        navigator.clipboard.writeText(item.prompt);
                                                                        alert("提示词已复制！");
                                                                    }
                                                                }}
                                                            >
                                                                复制
                                                            </Button>
                                                        </div>
                                                        <p className="text-zinc-600 dark:text-zinc-400 text-xs font-mono leading-relaxed line-clamp-3 hover:line-clamp-none transition-all cursor-text select-text bg-white dark:bg-zinc-950 p-2 rounded border border-zinc-200 dark:border-zinc-800">
                                                            {item.prompt}
                                                        </p>
                                                    </div>
                                                )}
                                            </div>
                                        ))
                                    ) : (
                                        <div className="col-span-full py-24 text-center">
                                            <ImageIcon className="h-12 w-12 mx-auto text-zinc-300 mb-4 opacity-20" />
                                            <p className="text-zinc-400">暂无生成的图片。</p>
                                        </div>
                                    );
                                })()}
                            </div>
                        </div>
                    ) : (
                        <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-10 shadow-sm min-h-[600px]">
                            {(() => {
                                // CRITICAL FIX: Correctly map activeTab to data key
                                const currentContent = activeTab === "design_generation" 
                                    ? data.design_proposals 
                                    : data[activeTab];
                                return renderTabContent(currentContent);
                            })()}
                        </div>
                    )}
                </div>
            </div>
        </div>
    </div>
  )

  if (project === null && status === "pending") return renderHome()
  // if (status === "in_progress" || (project !== null && status === "pending")) return renderLoading()
  
  if (status === "failed") {
      return (
        <div className="flex-1 flex flex-col items-center justify-center p-6 bg-zinc-50/50 dark:bg-zinc-950">
            <div className="text-center space-y-4 max-w-md">
                <div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto">
                    <Zap className="h-8 w-8 text-red-500" />
                </div>
                <h3 className="text-xl font-display font-bold text-zinc-900 dark:text-white">
                    任务运行失败
                </h3>
                <p className="text-zinc-500 dark:text-zinc-400 text-sm">
                    后端服务暂时无法响应，可能是因为 API Key 配置错误或网络超时。
                </p>
                <div className="flex gap-4 justify-center pt-4">
                    <Button variant="outline" onClick={() => {
                        setStatus("pending")
                        setProjectName("")
                        setBrief("")
                        // Reload page to reset state completely
                        window.location.reload()
                    }}>
                        返回首页
                    </Button>
                    <Button onClick={() => {
                        // Retry the last step? Currently we just reset to home for simplicity
                        // or user can try to run again if we kept the state
                        setStatus("pending")
                    }}>
                        重试
                    </Button>
                </div>
            </div>
        </div>
      )
  }

  return renderResults()
}
