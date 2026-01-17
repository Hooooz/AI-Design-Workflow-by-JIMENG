
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
  Share2
} from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@/lib/utils"

interface DashboardProps {
  project: string | null
  onProjectCreated: (projectName: string) => void
}

const STEPS = [
  { id: "market_analysis", label: "市场分析", icon: TrendingUp },
  { id: "visual_research", label: "视觉调研", icon: Palette },
  { id: "design_generation", label: "设计提案", icon: Sparkles },
  { id: "image_generation", label: "创意图库", icon: ImageIcon },
  { id: "full_report", label: "完整报告", icon: FileText },
]

export function Dashboard({ project, onProjectCreated }: DashboardProps) {
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState("image_generation")
  const [status, setStatus] = useState<string>("pending")
  const [currentStep, setCurrentStep] = useState<string>("")
  const [progress, setProgress] = useState(0)
  
  // Form State
  const [projectName, setProjectName] = useState("拍立得相机包")
  const [brief, setBrief] = useState("做一款拍立得相机包，需要参考市场中高端品牌的女性包包去结合设计一些相机包")
  const [modelName, setModelName] = useState("gemini-2.0-flash-exp")
  
  // Data State
  const [data, setData] = useState<Record<string, any>>({
    market_analysis: "",
    visual_research: "",
    design_proposals: "",
    full_report: "",
    images: []
  })

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

  const [tags, setTags] = useState<string[]>([])
  const [isAutocompleteLoading, setIsAutocompleteLoading] = useState(false)
  const [isTagsLoading, setIsTagsLoading] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  // Load Project Data
  useEffect(() => {
    if (project) {
      setLoading(true)
      fetch(`${API_URL}/api/project/${project}`)
        .then(res => res.json())
        .then(projectData => {
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
          
          // 修复：只有在当前项目确实需要刷新时才调用回调
          // 避免在切换项目时强制跳转回运行中的任务
          if (projectData.metadata.status === "in_progress" && project === projectData.metadata.project_name) {
             // 使用更智能的轮询机制而不是强制跳转
             const pollInterval = setInterval(() => {
               fetch(`${API_URL}/api/project/${project}`)
                 .then(res => res.json())
                 .then(updatedData => {
                   setStatus(updatedData.metadata.status)
                   setCurrentStep(updatedData.metadata.current_step)
                   setData(prev => ({
                     ...prev,
                     market_analysis: updatedData.market_analysis,
                     visual_research: updatedData.visual_research,
                     design_proposals: updatedData.design_proposals,
                     full_report: updatedData.full_report,
                     images: updatedData.images
                   }))
                   
                   if (updatedData.metadata.status !== "in_progress") {
                     clearInterval(pollInterval)
                   }
                 })
                 .catch(err => {
                   console.error("轮询失败:", err)
                   clearInterval(pollInterval)
                 })
             }, 2000) // 每2秒轮询一次
             
             // 清理函数
             return () => clearInterval(pollInterval)
          }
        })
        .catch(err => console.error(err))
        .finally(() => setLoading(false))
    } else {
      // Reset for new project
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
  }, [project])

  const handleAutocomplete = async () => {
    if (!brief) return
    setIsAutocompleteLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/ai/autocomplete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief, model_name: "gemini-2.5-flash-lite" })
      })
      const data = await res.json()
      if (data.expanded_brief) {
        setBrief(data.expanded_brief)
      }
    } catch (e) {
      console.error(e)
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
        body: JSON.stringify({ brief, model_name: "gemini-2.5-flash-lite" })
      })
      const data = await res.json()
      if (data.tags) {
        setTags(data.tags)
      }
    } catch (e) {
      console.error(e)
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

  const runStep = async (stepId: string) => {
    setLoading(true)
    setStatus("in_progress")
    setCurrentStep(stepId)
    try {
      const res = await fetch(`${API_URL}/api/workflow/step`, {
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
          }
        })
      })
      
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
    setProgress(10)
    
    try {
        // 修复：使用顺序执行并正确更新进度
        const steps = [
          { id: "market_analysis", progress: 30 },
          { id: "visual_research", progress: 50 },
          { id: "design_generation", progress: 70 },
          { id: "image_generation", progress: 90 },
          { id: "full_report", progress: 100 }
        ]
        
        for (const step of steps) {
          setCurrentStep(step.id)
          setProgress(step.progress)
          await runStep(step.id)
        }
        
        setStatus("completed")
    } catch (e) {
        setStatus("failed")
        console.error("运行失败:", e)
    } finally {
        setLoading(false)
    }
  }

  // --- Render Functions ---

  const renderHome = () => (
    <div className="flex-1 flex flex-col items-center justify-start p-6 overflow-y-auto custom-scrollbar bg-zinc-50/50 dark:bg-zinc-950">
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
                    <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                    <h2 className="text-xl font-display font-bold text-zinc-900 dark:text-white">
                        成果展示: {projectName}
                    </h2>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 text-sm text-emerald-600 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-100 dark:border-emerald-900 px-3 py-1.5 rounded-full font-medium">
                        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                        <span>生成完毕</span>
                    </div>
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
                        {STEPS.map(step => (
                            <button
                                key={step.id}
                                onClick={() => setActiveTab(step.id)}
                                className={cn(
                                    "px-6 py-2 text-[11px] font-bold rounded-md flex items-center gap-2 transition-all uppercase tracking-wider",
                                    activeTab === step.id 
                                        ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-white" 
                                        : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-300"
                                )}
                            >
                                <step.icon className="h-3.5 w-3.5" />
                                {step.label}
                            </button>
                        ))}
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
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {data.images && data.images.length > 0 ? (
                                data.images.map((img: string, idx: number) => (
                                    <div key={idx} className="group relative bg-white dark:bg-zinc-900 rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-800 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
                                        <div className="aspect-[4/5] overflow-hidden bg-zinc-100 dark:bg-zinc-800">
                                            <img 
                                                src={`${API_URL}${img}`} 
                                                alt={`Concept ${idx + 1}`}
                                                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                                            />
                                        </div>
                                        <div className="absolute inset-0 bg-gradient-to-t from-zinc-900/90 via-zinc-900/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-6">
                                            <div className="translate-y-4 group-hover:translate-y-0 transition-transform duration-300">
                                                <p className="text-white text-lg font-display font-bold">设计方案 {idx + 1}</p>
                                                <p className="text-zinc-300 text-xs mt-1">高保真创意渲染图</p>
                                                <div className="flex gap-2 mt-4">
                                                    <Button variant="secondary" size="sm" className="flex-1 font-bold text-[10px] uppercase tracking-wider" asChild>
                                                        <a href={`${API_URL}${img}`} download target="_blank">立即下载</a>
                                                    </Button>
                                                    <Button variant="secondary" size="icon" className="bg-white/20 backdrop-blur-md text-white border-none hover:bg-white/40">
                                                        <ExternalLink className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="col-span-full py-24 text-center">
                                    <ImageIcon className="h-12 w-12 mx-auto text-zinc-300 mb-4 opacity-20" />
                                    <p className="text-zinc-400">暂无生成的图片。</p>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-10 shadow-sm min-h-[600px]">
                            <div className="prose prose-zinc prose-lg max-w-none dark:prose-invert 
                                prose-headings:font-display prose-headings:font-bold prose-headings:tracking-tight 
                                prose-h1:text-4xl prose-h1:mb-8 prose-h1:pb-4 prose-h1:border-b prose-h1:border-zinc-100 dark:prose-h1:border-zinc-800
                                prose-h2:text-2xl prose-h2:mt-12 prose-h2:mb-6 prose-h2:flex prose-h2:items-center prose-h2:gap-3
                                prose-p:text-zinc-600 dark:prose-p:text-zinc-400 prose-p:leading-relaxed prose-p:mb-6
                                prose-li:text-zinc-600 dark:prose-li:text-zinc-400 prose-li:mb-2
                                prose-strong:text-zinc-900 dark:prose-strong:text-white
                                prose-blockquote:border-l-4 prose-blockquote:border-zinc-200 dark:prose-blockquote:border-zinc-700 prose-blockquote:bg-zinc-50 dark:prose-blockquote:bg-zinc-800/50 prose-blockquote:py-2 prose-blockquote:px-6 prose-blockquote:rounded-r-lg prose-blockquote:italic
                                prose-table:border prose-table:border-zinc-100 dark:prose-table:border-zinc-800 prose-table:rounded-xl prose-table:overflow-hidden
                                prose-th:bg-zinc-50 dark:prose-th:bg-zinc-800 prose-th:px-4 prose-th:py-3 prose-th:text-xs prose-th:font-bold prose-th:uppercase prose-th:tracking-wider
                                prose-td:px-4 prose-td:py-3 prose-td:text-sm prose-td:border-t prose-td:border-zinc-100 dark:prose-td:border-zinc-800">
                                {data[activeTab] ? (
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                            h1: ({ node, ...props }) => <h1 {...props} className="text-zinc-900 dark:text-white" />,
                                            h2: ({ node, ...props }) => (
                                                <h2 {...props} className="text-zinc-800 dark:text-zinc-100 group">
                                                    <span className="w-1.5 h-6 bg-zinc-900 dark:bg-zinc-100 rounded-full inline-block" />
                                                    {props.children}
                                                </h2>
                                            ),
                                            h3: ({ node, ...props }) => <h3 {...props} className="text-zinc-800 dark:text-zinc-200 mt-8 mb-4 font-bold" />,
                                            img: ({ node, ...props }) => {
                                                const src = typeof props.src === 'string' ? props.src : '';
                                                const isRelative = src && !src.startsWith('http') && !src.startsWith('https') && !src.startsWith('/');
                                                const finalSrc = isRelative ? `${API_URL}/projects/${project}/${src}` : src;
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
                                        {data[activeTab]}
                                    </ReactMarkdown>
                                ) : (
                                    <div className="py-24 text-center text-zinc-300">
                                        <FileText className="h-12 w-12 mx-auto mb-4 opacity-20" />
                                        <p>该章节暂无内容。</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    </div>
  )

  if (project === null && status === "pending") return renderHome()
  if (status === "in_progress") return renderLoading()
  return renderResults()
}
