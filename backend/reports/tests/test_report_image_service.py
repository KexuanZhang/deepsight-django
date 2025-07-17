import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from notebooks.models import Notebook, KnowledgeBaseItem, KnowledgeBaseImage
from reports.models import Report, ReportImage
from reports.core.report_image_service import ReportImageService

User = get_user_model()


class ReportImageServiceTest(TestCase):
    """Test cases for ReportImageService"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test notebook
        self.notebook = Notebook.objects.create(
            user=self.user,
            name='Test Notebook',
            description='Test notebook for image tests'
        )
        
        # Create knowledge base item
        self.kb_item = KnowledgeBaseItem.objects.create(
            user=self.user,
            title='Test KB Item',
            content_type='document',
            content='Test content with images'
        )
        
        # Create test images with specific figure_ids
        self.figure_id_1 = uuid.uuid4()
        self.figure_id_2 = uuid.uuid4()
        
        self.kb_image_1 = KnowledgeBaseImage.objects.create(
            figure_id=self.figure_id_1,
            knowledge_base_item=self.kb_item,
            image_caption='Test Image 1',
            minio_object_key='test/images/image1.jpg',
            content_type='image/jpeg',
            file_size=1024
        )
        
        self.kb_image_2 = KnowledgeBaseImage.objects.create(
            figure_id=self.figure_id_2,
            knowledge_base_item=self.kb_item,
            image_caption='Test Image 2',
            minio_object_key='test/images/image2.png',
            content_type='image/png',
            file_size=2048
        )
        
        # Create test report
        self.report = Report.objects.create(
            user=self.user,
            notebooks=self.notebook,
            article_title='Test Report',
            topic='Test Topic',
            include_image=True,
            status=Report.STATUS_PENDING
        )
        
        # Initialize service
        self.service = ReportImageService()
    
    def test_extract_figure_ids_from_content(self):
        """Test extracting figure IDs from content"""
        content = f"""
        # Test Report
        
        Here is an image: {self.figure_id_1}
        
        And another one: <{self.figure_id_2}>
        
        Some text without images.
        """
        
        figure_ids = self.service.extract_figure_ids_from_content(content)
        
        self.assertEqual(len(figure_ids), 2)
        self.assertIn(str(self.figure_id_1), figure_ids)
        self.assertIn(str(self.figure_id_2), figure_ids)
    
    def test_find_images_by_figure_ids(self):
        """Test finding images by figure IDs"""
        figure_ids = [str(self.figure_id_1), str(self.figure_id_2)]
        
        images = self.service.find_images_by_figure_ids(figure_ids, self.user.id)
        
        self.assertEqual(len(images), 2)
        self.assertEqual(images[0].figure_id, self.figure_id_1)
        self.assertEqual(images[1].figure_id, self.figure_id_2)
    
    def test_insert_figure_images(self):
        """Test inserting figure images into content"""
        # Create ReportImage records first
        report_image_1 = ReportImage.objects.create(
            figure_id=self.figure_id_1,
            report=self.report,
            image_caption=self.kb_image_1.image_caption,
            minio_object_key=f'reports/{self.report.id}/images/{self.figure_id_1}.jpg',
            content_type=self.kb_image_1.content_type,
            file_size=self.kb_image_1.file_size,
            source_minio_object_key=self.kb_image_1.minio_object_key
        )
        
        content = f"Here is an image: {self.figure_id_1}"
        
        updated_content = self.service.insert_figure_images(content, [report_image_1])
        
        # Check that figure ID was replaced with img tag
        self.assertNotIn(str(self.figure_id_1), updated_content)
        self.assertIn('<img', updated_content)
        self.assertIn('data-figure-id=', updated_content)
        self.assertIn('Test Image 1', updated_content)  # Caption should be in alt text
    
    def test_process_report_images_no_images(self):
        """Test processing report with no images"""
        content = "This is a report without any images."
        
        report_images, updated_content = self.service.process_report_images(self.report, content)
        
        self.assertEqual(len(report_images), 0)
        self.assertEqual(content, updated_content)
    
    def test_cleanup_report_images(self):
        """Test cleaning up report images"""
        # Create a report image
        report_image = ReportImage.objects.create(
            figure_id=self.figure_id_1,
            report=self.report,
            image_caption='Test cleanup',
            minio_object_key=f'reports/{self.report.id}/images/test.jpg',
            content_type='image/jpeg',
            file_size=1024
        )
        
        # Verify image exists
        self.assertEqual(ReportImage.objects.filter(report=self.report).count(), 1)
        
        # Clean up
        self.service.cleanup_report_images(self.report)
        
        # Verify image was deleted
        self.assertEqual(ReportImage.objects.filter(report=self.report).count(), 0)