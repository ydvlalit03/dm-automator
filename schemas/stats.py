from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_campaigns: int
    active_campaigns: int
    total_comments: int
    total_dms_sent: int
    total_dms_failed: int
    total_pending_manual: int
    ig_campaigns: int
    linkedin_campaigns: int
