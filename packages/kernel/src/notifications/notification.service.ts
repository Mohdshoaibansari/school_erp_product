import { PrismaClient, NotificationTemplate, NotificationDelivery, NotificationStatus } from '@school-erp/database';

export interface SendNotificationInput {
  tenantId: string;
  institutionId?: string;
  recipientEmail: string;
  recipientUserId?: string;
  templateCode: string;
  data: Record<string, any>;
}

export interface EmailProvider {
  sendEmail(to: string, subject: string, body: string): Promise<boolean>;
}

export class NotificationService {
  constructor(
    private prisma: PrismaClient,
    private emailProvider?: EmailProvider
  ) {}

  async send(input: SendNotificationInput): Promise<NotificationDelivery> {
    const { tenantId, institutionId, recipientEmail, recipientUserId, templateCode, data } = input;

    // Get template
    const template = await this.prisma.notificationTemplate.findUnique({
      where: { code: templateCode },
    });

    if (!template) {
      throw new Error(`Notification template "${templateCode}" not found`);
    }

    if (!template.isActive) {
      throw new Error(`Notification template "${templateCode}" is inactive`);
    }

    // Render template
    const subject = this.render(template.subject, data);
    const body = this.render(template.body, data);

    // Create delivery record
    const delivery = await this.prisma.notificationDelivery.create({
      data: {
        tenantId,
        institutionId,
        recipientEmail,
        recipientUserId,
        templateCode,
        subject,
        body,
        status: 'PENDING',
      },
    });

    // Send email
    try {
      if (!this.emailProvider) {
        throw new Error('Email provider not configured');
      }

      const sent = await this.emailProvider.sendEmail(recipientEmail, subject, body);

      if (sent) {
        return this.prisma.notificationDelivery.update({
          where: { id: delivery.id },
          data: {
            status: 'SENT',
            sentAt: new Date(),
          },
        });
      } else {
        return this.prisma.notificationDelivery.update({
          where: { id: delivery.id },
          data: {
            status: 'FAILED',
            error: 'Email provider returned false',
          },
        });
      }
    } catch (error) {
      return this.prisma.notificationDelivery.update({
        where: { id: delivery.id },
        data: {
          status: 'FAILED',
          error: error instanceof Error ? error.message : 'Unknown error',
        },
      });
    }
  }

  private render(template: string, data: Record<string, any>): string {
    let result = template;
    for (const [key, value] of Object.entries(data)) {
      const placeholder = `{{${key}}}`;
      result = result.replace(new RegExp(placeholder, 'g'), String(value));
    }
    return result;
  }

  async createTemplate(data: {
    tenantId?: string;
    code: string;
    name: string;
    subject: string;
    body: string;
  }): Promise<NotificationTemplate> {
    return this.prisma.notificationTemplate.create({
      data,
    });
  }

  async getTemplate(code: string): Promise<NotificationTemplate | null> {
    return this.prisma.notificationTemplate.findUnique({
      where: { code },
    });
  }

  async getDeliveries(
    tenantId: string,
    options: { recipientUserId?: string; status?: NotificationStatus; skip?: number; take?: number } = {}
  ): Promise<NotificationDelivery[]> {
    const { recipientUserId, status, skip = 0, take = 50 } = options;

    return this.prisma.notificationDelivery.findMany({
      where: {
        tenantId,
        ...(recipientUserId ? { recipientUserId } : {}),
        ...(status ? { status } : {}),
      },
      skip,
      take,
      orderBy: { createdAt: 'desc' },
    });
  }

  setEmailProvider(provider: EmailProvider): void {
    this.emailProvider = provider;
  }
}
