import React, { useState } from 'react';
import { Report } from '../types/type';
import { Trash2 } from 'lucide-react';

interface ReportEditorProps {
  report: Report;
  onBack: () => void;
  onDelete: (report: Report) => void;
  onSave: (report: Report, content: string) => void;
}

const ReportEditor: React.FC<ReportEditorProps> = ({ 
  report, 
  onBack, 
  onDelete, 
  onSave 
}) => {
  const [content, setContent] = useState(report.content || report.markdown_content || '');
  const [isEditing, setIsEditing] = useState(false);

  const handleSave = () => {
    onSave(report, content);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setContent(report.content || report.markdown_content || '');
    setIsEditing(false);
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <span>Studio</span>
            <span>›</span>
            <span>Note</span>
          </div>
          
          <button
            onClick={() => onDelete(report)}
            className="p-2 text-gray-400 hover:text-red-600 transition-colors"
            title="Delete report"
          >
            <Trash2 className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Title */}
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          {report.title || report.article_title || '大模型与生成式AI研究进展'}
        </h1>
        
        {/* Status Message */}
        <p className="text-sm text-gray-600 mb-6">
          (Saved responses are view only)
        </p>

        {/* Introduction Section */}
        <div className="mb-8">
          <p className="text-gray-700 leading-relaxed mb-4">
            好的,以下是根据您提供的资料整理的详细时间线和人物列表: 详细时间线说明: 本时间线
          </p>
          
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-semibold text-gray-900 mb-2">说明:</h3>
            <p className="text-sm text-gray-700 leading-relaxed">
              本时间线按照事件发生的时间顺序列出,主要侧重于各项技术和模型的提出、改进以及其应用领域。由于来源材料是技术论文摘要,因此"事件"主要指研究成果的发表和相关技术的开发。
            </p>
          </div>
        </div>

        {/* Content Section */}
        <div className="space-y-6">
          {isEditing ? (
            <div>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="w-full h-96 p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your report content..."
              />
              <div className="flex space-x-4 mt-4">
                <button
                  onClick={handleSave}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Save
                </button>
                <button
                  onClick={handleCancel}
                  className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div>
              {/* Sample Timeline Items */}
              <div className="space-y-4">
                <div className="border-l-4 border-blue-500 pl-4">
                  <h4 className="font-semibold text-gray-900 mb-2">
                    未知具体日期(早期研究)学习平衡短期和长期奖励的最优策略 (Index 19):
                  </h4>
                  <p className="text-gray-700 leading-relaxed">
                    提出了一种新颖的分解策略学习方法(DPPL),通过将长期奖励分解为短期奖励来学习最优策略。该方法在多个强化学习任务中表现出色,特别是在需要平衡短期和长期回报的场景中。
                  </p>
                </div>

                <div className="border-l-4 border-blue-500 pl-4">
                  <h4 className="font-semibold text-gray-900 mb-2">
                    推荐系统中用户-创作者特征两极分化与双重影响 (Index 88):
                  </h4>
                  <p className="text-gray-700 leading-relaxed">
                    揭示了一个模型,展示了导致两极分化和多样性损失的双重影响。该研究分析了推荐系统中用户和创作者特征的动态变化,为理解推荐算法的社会影响提供了新的视角。
                  </p>
                </div>

                <div className="border-l-4 border-blue-500 pl-4">
                  <h4 className="font-semibold text-gray-900 mb-2">
                    大型语言模型中一致性现象的揭示 (Index 385):
                  </h4>
                  <p className="text-gray-700 leading-relaxed">
                    使用ConBench揭示大型视觉语言模型(LVLMs)中的不一致性。该研究开发了一个新的基准测试框架,用于评估和比较不同模型在一致性方面的表现。
                  </p>
                </div>

                <div className="border-l-4 border-blue-500 pl-4">
                  <h4 className="font-semibold text-gray-900 mb-2">
                    图像值得32个令牌用于重建和生成 (Index 416):
                  </h4>
                  <p className="text-gray-700 leading-relaxed">
                    介绍了一种基于Transformer的一维标记器(TiTok),用于图像标记化。该方法能够有效地将图像转换为令牌序列,为图像重建和生成任务提供了新的方法。
                  </p>
                </div>

                <div className="border-l-4 border-blue-500 pl-4">
                  <h4 className="font-semibold text-gray-900 mb-2">
                    Chat-Scene:通过对象标识符连接3D场景和大型语言模型 (Index 440):
                  </h4>
                  <p className="text-gray-700 leading-relaxed">
                    介绍了一种在对象级别与3D场景交互的方法。该方法通过对象标识符将3D场景与大型语言模型连接起来,实现了更自然和直观的3D场景理解。
                  </p>
                </div>
              </div>

              <div className="mt-6">
                <button
                  onClick={() => setIsEditing(true)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Edit Report
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReportEditor; 