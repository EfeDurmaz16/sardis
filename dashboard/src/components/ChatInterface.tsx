
import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2, AlertCircle, CheckCircle } from 'lucide-react'
import clsx from 'clsx'
import { useInstructAgent } from '../hooks/useApi'
import { getErrorMessage } from '../utils/errors'

type ToolCall = {
    name?: string
    arguments?: Record<string, unknown>
}

interface Message {
    id: string
    role: 'user' | 'agent'
    content: string
    timestamp: Date
    status?: 'sending' | 'sent' | 'error'
    toolCall?: ToolCall
    txId?: string
}

interface ChatInterfaceProps {
    agentId: string
    agentName: string
    onClose: () => void
}

export default function ChatInterface({ agentId, agentName, onClose }: ChatInterfaceProps) {
    const [input, setInput] = useState('')
    const [messages, setMessages] = useState<Message[]>([
        {
            id: 'welcome',
            role: 'agent',
            content: `Hello! I'm ${agentName}. How can I help you manage your finances today?`,
            timestamp: new Date()
        }
    ])

    const messagesEndRef = useRef<HTMLDivElement>(null)
    const instructAgent = useInstructAgent()

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!input.trim() || instructAgent.isPending) return

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input,
            timestamp: new Date(),
            status: 'sending'
        }

        setMessages(prev => [...prev, userMessage])
        setInput('')

        try {
            const result = await instructAgent.mutateAsync({
                agentId,
                instruction: userMessage.content
            })

            // Update user message status
            setMessages(prev => prev.map(m =>
                m.id === userMessage.id ? { ...m, status: 'sent' } : m
            ))

            // Add agent response
            if (result.error) {
                setMessages(prev => [...prev, {
                    id: Date.now().toString(),
                    role: 'agent',
                    content: `Error: ${result.error}`,
                    timestamp: new Date(),
                    status: 'error'
                }])
            } else {
                const content = result.response || (result.tool_call ?
                    `Executed tool: ${result.tool_call.name}` :
                    "I processed your request but have no specific response.")

                setMessages(prev => [...prev, {
                    id: Date.now().toString(),
                    role: 'agent',
                    content,
                    timestamp: new Date(),
                    toolCall: result.tool_call,
                    txId: result.tx_id
                }])
            }

        } catch (error: unknown) {
            setMessages(prev => prev.map(m =>
                m.id === userMessage.id ? { ...m, status: 'error' } : m
            ))
            setMessages(prev => [...prev, {
                id: Date.now().toString(),
                role: 'agent',
                content: `Failed to process request: ${getErrorMessage(error, 'Unknown error')}`,
                timestamp: new Date(),
                status: 'error'
            }])
        }
    }

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="card w-full max-w-2xl mx-4 h-[600px] flex flex-col overflow-hidden shadow-2xl border border-dark-100">
                {/* Header */}
                <div className="p-4 border-b border-dark-100 flex items-center justify-between bg-dark-200">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center">
                            <Bot className="w-6 h-6 text-sardis-400" />
                        </div>
                        <div>
                            <h3 className="font-bold text-white">{agentName}</h3>
                            <p className="text-xs text-sardis-400 flex items-center gap-1">
                                <span className="w-2 h-2 rounded-full bg-sardis-500 animate-pulse" />
                                Online
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-white transition-colors"
                    >
                        Close
                    </button>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-dark-300">
                    {messages.map((msg) => (
                        <div
                            key={msg.id}
                            className={clsx(
                                "flex gap-3 max-w-[80%]",
                                msg.role === 'user' ? "ml-auto flex-row-reverse" : ""
                            )}
                        >
                            <div className={clsx(
                                "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                                msg.role === 'agent' ? "bg-sardis-500/10 text-sardis-400" : "bg-dark-100 text-gray-400"
                            )}>
                                {msg.role === 'agent' ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                            </div>

                            <div className={clsx(
                                "rounded-2xl p-4 text-sm",
                                msg.role === 'user'
                                    ? "bg-sardis-600 text-white rounded-tr-none"
                                    : "bg-dark-200 text-gray-200 rounded-tl-none border border-dark-100"
                            )}>
                                <p className="whitespace-pre-wrap">{msg.content}</p>

                                {/* Tool Call Details */}
                                {msg.toolCall && (
                                    <div className="mt-3 pt-3 border-t border-dark-100/50 text-xs font-mono">
                                        <div className="flex items-center gap-2 text-sardis-300 mb-1">
                                            <CheckCircle className="w-3 h-3" />
                                            Tool Executed: {msg.toolCall.name}
                                        </div>
                                        <pre className="bg-black/20 p-2 rounded overflow-x-auto text-gray-400">
                                            {JSON.stringify(msg.toolCall.arguments, null, 2)}
                                        </pre>
                                    </div>
                                )}

                                {/* Transaction ID */}
                                {msg.txId && (
                                    <div className="mt-2 text-xs text-sardis-300 flex items-center gap-1">
                                        <CheckCircle className="w-3 h-3" />
                                        Transaction: {msg.txId.substring(0, 8)}...
                                    </div>
                                )}

                                <div className={clsx(
                                    "text-[10px] mt-1 opacity-50 flex items-center gap-1",
                                    msg.role === 'user' ? "text-white justify-end" : "text-gray-400"
                                )}>
                                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    {msg.status === 'error' && <AlertCircle className="w-3 h-3 text-red-400" />}
                                </div>
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <form onSubmit={handleSend} className="p-4 bg-dark-200 border-t border-dark-100">
                    <div className="relative flex items-center gap-2">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Type your instruction..."
                            className="flex-1 bg-dark-300 border border-dark-100 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50 transition-colors"
                            disabled={instructAgent.isPending}
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || instructAgent.isPending}
                            className="p-3 bg-sardis-500 text-white rounded-xl hover:bg-sardis-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {instructAgent.isPending ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                <Send className="w-5 h-5" />
                            )}
                        </button>
                    </div>
                    <p className="text-xs text-gray-500 mt-2 text-center">
                        AI agents can execute real transactions. Please verify instructions carefully.
                    </p>
                </form>
            </div>
        </div>
    )
}
