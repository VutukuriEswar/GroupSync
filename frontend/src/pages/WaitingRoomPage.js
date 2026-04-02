import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate, useParams } from 'react-router-dom';
import { getGroupMembers } from '@/utils/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, Users, CheckCircle2, Clock } from 'lucide-react';
import { toast } from 'sonner';

const WaitingRoomPage = () => {
  const { groupId } = useParams();
  const navigate = useNavigate();
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [submitted, setSubmitted] = useState(0);

  useEffect(() => {
    const fetchMembers = async () => {
      try {
        const response = await getGroupMembers(groupId);
        setMembers(response.data.members);
        setTotal(response.data.total);
        setSubmitted(response.data.submitted);
        setLoading(false);

        if (response.data.submitted >= response.data.total) {
          toast.success('Everyone is ready!');
          setTimeout(() => {
            navigate(`/group/${groupId}/recommendations`);
          }, 1500);
        }
      } catch (error) {
        toast.error('Failed to load group status');
      }
    };

    fetchMembers();
    const interval = setInterval(fetchMembers, 3000);

    return () => clearInterval(interval);
  }, [groupId, navigate]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 flex items-center justify-center">
        <Loader2 className="w-12 h-12 animate-spin text-primary" />
      </div>
    );
  }

  const progress = (submitted / total) * 100;

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-2xl"
      >
        <Card className="glass border-2">
          <CardHeader className="text-center">
            <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <Clock className="w-10 h-10 text-primary" />
            </div>
            <CardTitle className="text-3xl font-outfit font-bold" data-testid="waiting-room-title">
              Waiting for Everyone
            </CardTitle>
            <p className="text-muted-foreground mt-2">
              We'll generate recommendations once all members have shared their preferences
            </p>
          </CardHeader>
          <CardContent className="space-y-8">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-lg font-semibold" data-testid="progress-text">
                  {submitted} of {total} completed
                </span>
                <span className="text-lg font-bold text-primary">{Math.round(progress)}%</span>
              </div>
              <div className="h-4 bg-muted rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.5 }}
                  className="h-full bg-gradient-to-r from-primary to-accent"
                  data-testid="progress-bar"
                />
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Users className="w-5 h-5" />
                Group Members
              </h3>
              <div className="space-y-2">
                {members.map((member, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    className="glass p-4 rounded-xl flex items-center justify-between"
                    data-testid={`member-${idx}`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center font-semibold">
                        {member.id.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium">{member.id.startsWith('guest') ? 'Guest' : 'Member'} {idx + 1}</p>
                        <p className="text-sm text-muted-foreground capitalize">{member.role}</p>
                      </div>
                    </div>
                    {member.preferences_submitted ? (
                      <CheckCircle2 className="w-6 h-6 text-primary" data-testid={`member-${idx}-status-complete`} />
                    ) : (
                      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" data-testid={`member-${idx}-status-pending`} />
                    )}
                  </motion.div>
                ))}
              </div>
            </div>

            {submitted >= total && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
              >
                <Button
                  className="w-full rounded-full text-lg h-12 shadow-lg shadow-primary/20"
                  onClick={() => navigate(`/group/${groupId}/recommendations`)}
                  data-testid="view-recommendations-btn"
                >
                  View Recommendations
                </Button>
              </motion.div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
};

export default WaitingRoomPage;